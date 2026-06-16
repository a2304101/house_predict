import os

folder_path = f"kaggle/working"  # 你可以改成特定的路徑
size_limit = 700 * 1024  # 700KB 轉成 Bytes
small_files=[]
# for root, dirs, files in os.walk(folder_path):
#     for file in files:
#         file_path = os.path.join(root, file)
#         if os.path.getsize(file_path) < size_limit:
#             print(f"檔案: {file_path}, 大小: {os.path.getsize(file_path)/1024:.2f} KB")
#             small_files.append(file)

# with open("small_files.txt", "w", encoding="utf-8") as f:
#     if small_files:
#         f.write("\n".join(small_files))
#         print(f"\n--- 已將 {len(small_files)} 筆檔名存入 small_files.txt ---")
            