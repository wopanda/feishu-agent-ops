#!/usr/bin/env python3
import argparse


def main() -> None:
    ap = argparse.ArgumentParser(description='Render compact final reply.')
    ap.add_argument('--status', required=True, choices=['done', 'issue'])
    ap.add_argument('--evidence', required=True)
    ap.add_argument('--next-step', default='')
    args = ap.parse_args()

    line1 = '已完成。' if args.status == 'done' else '发现问题。'
    line2 = f'关键依据：{args.evidence.strip()}'
    print(line1)
    print(line2)
    if args.next_step.strip():
        print(args.next_step.strip())


if __name__ == '__main__':
    main()
