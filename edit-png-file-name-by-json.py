import os
import re

def rename_images():
    # 定义目录路径
    images_dir = "data/images/refs/"
    refs_dir = "data/refs/"
    
    # 获取所有JSON引用文件
    json_files = [f for f in os.listdir(refs_dir) if f.endswith('.json')]
    
    # 创建编号到完整文件名的映射
    number_to_name = {}
    
    for json_file in json_files:
        # 从JSON文件名中提取编号（最后的部分）
        match = re.search(r'(\d+(?:-\d+)?)\.json$', json_file)
        if match:
            number = match.group(1)
            # 去掉.json扩展名，保留完整的引用名称
            full_name = json_file.replace('.json', '.png')
            number_to_name[number] = full_name
    
    # 重命名图片文件
    for image_file in os.listdir(images_dir):
        if image_file.endswith('.png'):
            # 提取图片文件的编号部分（去掉.png）
            image_number = image_file.replace('.png', '')
            
            if image_number in number_to_name:
                old_path = os.path.join(images_dir, image_file)
                new_path = os.path.join(images_dir, number_to_name[image_number])
                
                # 重命名文件
                os.rename(old_path, new_path)
                print(f"重命名: {image_file} -> {number_to_name[image_number]}")
            else:
                print(f"警告: 未找到图片 {image_file} 对应的引用文件")

if __name__ == "__main__":
    rename_images()