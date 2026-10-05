#!/usr/bin/env python3
"""golfsol —— 终端高尔夫纸牌接龙。

规则（标准 Golf Solitaire 的小幅简化）：
- 52 张牌：35 张发到牌桌（5 列 × 7 行，只有每列最底下一张可走），
  剩下 17 张是牌堆（stock）。开局废牌堆（waste）为空，先摸一张。
- 可走：某列当前最底下（暴露）的牌，与废牌堆顶的点数相差恰好 1（向上或向下）。
- A 为最小（1），K 为最大（13）；K 和 A 之间没有回绕（有意选择）。
- 无法走牌时从牌堆摸一张到废牌堆；牌堆摸完且无可走牌则终局。
- 胜利：35 张牌桌牌全部移走。得分 = 剩余牌桌牌数（越低越好，0 为全胜）。
"""

import argparse
import random
import secrets
import sys

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["♠", "♥", "♦", "♣"]
RANK_VALUE = {r: i + 1 for i, r in enumerate(RANKS)}

COLS, ROWS = 5, 7
TABLEAU = COLS * ROWS  # 35
STOCK = 17


def new_deck():
    return [(r, s) for s in SUITS for r in RANKS]


def card_name(card):
    return f"{card[0]}{card[1]}"


def adjacent(a, b):
    """点数相邻（无回绕：K-A 不算相邻）。"""
    return abs(RANK_VALUE[a[0]] - RANK_VALUE[b[0]]) == 1


class Game:
    def __init__(self, seed=None):
        rng = random.Random(seed)
        deck = new_deck()
        rng.shuffle(deck)
        # tableau: 5 列，每列 7 张；列内索引 6 是最底下（先暴露）。
        self.tableau = [[deck[c * ROWS + r] for r in range(ROWS)] for c in range(COLS)]
        # 每列"已移走"数量（从最底下开始数）
        self.removed = [0] * COLS
        self.stock = deck[TABLEAU:]
        assert len(self.stock) == STOCK, f"stock 应为 {STOCK}，实际 {len(self.stock)}"
        self.waste = None
        self.draws = 0

    def exposed(self, col):
        """某列当前暴露的牌（最底下未移走的），没有则返回 None。"""
        if self.removed[col] >= ROWS:
            return None
        return self.tableau[col][ROWS - 1 - self.removed[col]]

    def exposed_cards(self):
        return {c: self.exposed(c) for c in range(COLS)}

    def draw(self):
        """从牌堆摸一张到废牌堆。返回 False 表示牌堆已空。"""
        if not self.stock:
            return False
        self.waste = self.stock.pop()
        self.draws += 1
        return True

    def legal_moves(self):
        """返回当前可走的列索引列表。"""
        if self.waste is None:
            return []
        return [c for c in range(COLS)
                if (card := self.exposed(c)) is not None and adjacent(card, self.waste)]

    def remove(self, col):
        """移走某列暴露的牌。非法返回 False。"""
        if col not in range(COLS):
            return False
        card = self.exposed(col)
        if card is None or self.waste is None or not adjacent(card, self.waste):
            return False
        self.removed[col] += 1
        self.waste = card
        return True

    def remaining(self):
        return TABLEAU - sum(self.removed)

    def won(self):
        return self.removed == [ROWS] * COLS

    def stuck(self):
        return not self.stock and not self.legal_moves()


def render(g):
    lines = []
    lines.append("牌桌（列 1-5，底牌可走）:")
    # 画成行：顶行 row0 ... 底行 row6；移走的画空白
    for r in range(ROWS):
        row = []
        for c in range(COLS):
            gone = r >= ROWS - g.removed[c]
            row.append("   " if gone else card_name(g.tableau[c][r]).rjust(3))
        lines.append(" ".join(row))
    lines.append(f"废牌堆顶: {card_name(g.waste) if g.waste else '(空)'}   "
                 f"牌堆剩: {len(g.stock)}   剩余牌桌: {g.remaining()}   已摸: {g.draws}")
    return "\n".join(lines)


def auto_play(seed=None, verbose=False):
    """贪心机器人：优先移走能暴露更多牌的列（即移走数最少的列先）。"""
    g = Game(seed)
    g.draw()
    steps = 0
    while True:
        moves = g.legal_moves()
        if moves:
            # 贪心：选已移走最少的列（暴露新牌最慢？不——选 removed 最小的列
            # 保持各列均衡，这里简单选第一列即可；为可复现选 removed 最小）
            col = min(moves, key=lambda c: g.removed[c])
            g.remove(col)
            steps += 1
        elif not g.draw():
            break
        steps += 1
        if steps > 10000:
            raise RuntimeError("auto 循环保护触发")
    result = {"won": g.won(), "remaining": g.remaining(),
              "draws": g.draws, "steps": steps}
    if verbose:
        print(render(g))
        print(f"自动游玩结束: {'胜利' if g.won() else '失败'}, "
              f"剩余 {g.remaining()} 张, 摸牌 {g.draws} 次。")
    return result


def play_interactive(seed=None):
    if not sys.stdin.isatty():
        print("error: 交互模式需要终端；管道/脚本场景请用 --auto。", file=sys.stderr)
        return 2
    g = Game(seed)
    print("高尔夫接龙：输入列号 1-5 移走该列底牌，d 摸牌，q 退出。")
    print("规则：只能移走与废牌堆顶点数相差 1 的牌（K-A 无回绕）。")
    if not g.draw():
        print("error: 牌堆为空，无法开局。", file=sys.stderr)
        return 1
    while True:
        print()
        print(render(g))
        if g.won():
            print(f"🎉 胜利！35 张全部移走，共摸牌 {g.draws} 次。")
            return 0
        moves = g.legal_moves()
        if moves:
            print(f"可走列: {' '.join(str(c + 1) for c in moves)}")
        else:
            print("无可走牌。", end=" ")
            if not g.stock:
                print(f"终局：剩余 {g.remaining()} 张牌桌牌。得分 {g.remaining()}。")
                return 0
        try:
            cmd = input("走哪列 (1-5/d摸牌/q退出): ").strip().lower()
        except EOFError:
            print()
            return 0
        if cmd in ("q", "quit", "退出"):
            print(f"退出。剩余 {g.remaining()} 张。")
            return 0
        if cmd in ("d", "摸", "摸牌"):
            if not g.draw():
                print("牌堆已空。")
            continue
        if cmd.isdigit() and 1 <= int(cmd) <= COLS:
            if g.remove(int(cmd) - 1):
                continue
            print("非法：该列底牌与废牌堆顶不相邻。")
            continue
        print("输入无效：请输入 1-5、d 或 q。")


def main(argv=None):
    ap = argparse.ArgumentParser(description="终端高尔夫纸牌接龙")
    ap.add_argument("--seed", type=int, default=None, help="随机种子")
    ap.add_argument("--auto", action="store_true", help="贪心机器人自动游玩")
    args = ap.parse_args(argv)
    if args.auto:
        auto_play(args.seed, verbose=True)
        return 0
    return play_interactive(args.seed)


if __name__ == "__main__":
    raise SystemExit(main())
