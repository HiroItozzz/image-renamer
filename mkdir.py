"""テストケースのフォルダを一括作成するスクリプト"""

from pathlib import Path

BASE_NAME = "G002-{:0>4}〜G002-{:0>4}"

new_dir_nums = []
while True:
    start_num_str = input("テストケースグループの最初のテストケースNoを入力: ")
    if start_num_str == "":
        break
    try:
        start_num = int(start_num_str)
    except ValueError:
        print("不正な値です")
        continue
    new_dir_nums.append(start_num)

new_dir_names = [
    Path("/home/hiro/Pictures")
    / BASE_NAME.format(new_dir_nums[n], new_dir_nums[n + 1] - 1)
    for n in range(len(new_dir_nums) - 1)
]

for out_dir in new_dir_names:
    out_dir.mkdir(exist_ok=True)
    print(f"フォルダ {out_dir.name} を作成しました")
