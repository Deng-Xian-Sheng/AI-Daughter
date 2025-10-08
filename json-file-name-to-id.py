import os
import json
import argparse
from pathlib import Path

def update_json_ids(directory_path):
    """
    读取指定目录下的所有json文件，将文件名（不含扩展名）覆盖到json内容中的id字段
    
    Args:
        directory_path (str): 要处理的目录路径
    """
    # 将路径转换为Path对象以便更好地处理
    directory = Path(directory_path)
    
    # 检查目录是否存在
    if not directory.exists():
        print(f"错误：目录 '{directory_path}' 不存在")
        return
    
    if not directory.is_dir():
        print(f"错误： '{directory_path}' 不是一个目录")
        return
    
    # 查找所有json文件
    json_files = list(directory.glob("*.json"))
    
    if not json_files:
        print(f"在目录 '{directory_path}' 中没有找到任何json文件")
        return
    
    print(f"找到 {len(json_files)} 个json文件，开始处理...")
    
    processed_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            # 获取文件名（不含扩展名）
            filename_without_ext = json_file.stem
            
            # 读取JSON文件内容
            with open(json_file, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"错误：文件 '{json_file.name}' 不是有效的JSON格式 - {e}")
                    error_count += 1
                    continue
            
            # 更新id字段
            if isinstance(data, dict):
                data['id'] = filename_without_ext
            else:
                print(f"警告：文件 '{json_file.name}' 的根元素不是对象，跳过处理")
                error_count += 1
                continue
            
            # 写回文件
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"已更新：{json_file.name} -> id: {filename_without_ext}")
            processed_count += 1
            
        except Exception as e:
            print(f"处理文件 '{json_file.name}' 时发生错误：{e}")
            error_count += 1
    
    print(f"\n处理完成！")
    print(f"成功处理：{processed_count} 个文件")
    print(f"处理失败：{error_count} 个文件")

def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description='更新JSON文件中的id字段为文件名')
    parser.add_argument('directory', help='要处理的目录路径')
    
    args = parser.parse_args()
    
    update_json_ids(args.directory)

if __name__ == "__main__":
    # 如果直接运行脚本，可以使用默认目录或通过命令行参数指定
    import sys
    
    if len(sys.argv) > 1:
        main()
    else:
        # 如果没有提供命令行参数，可以在这里设置默认目录
        default_directory = input("请输入要处理的目录路径（或直接按回车使用当前目录）: ").strip()
        
        if not default_directory:
            print("必须传入待处理目录！")
            exit(1)
        
        update_json_ids(default_directory)