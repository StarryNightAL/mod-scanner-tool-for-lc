import os
import re
import sys
from datetime import datetime
import common   # 导入公共模块

def extract_equipment_ids_and_info(file_path):
    """
    从XML或TXT文件中提取equipment id和其他信息
    返回值: (weapon_ids, armor_ids, file_info)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as file:
                content = file.read()
        except:
            print(f"无法读取文件: {file_path}", file=sys.stderr)
            return [], [], {}
    except Exception as e:
        print(f"读取文件出错 {file_path}: {e}", file=sys.stderr)
        return [], [], {}
    
    # 匹配 weapon 类型的 equipment id
    weapon_pattern = r'<equipment id="(\d+)"[^>]*type="weapon">'
    weapon_matches = re.findall(weapon_pattern, content)
    
    # 匹配 armor 类型的 equipment id
    armor_pattern = r'<equipment id="(\d+)"[^>]*type="armor">'
    armor_matches = re.findall(armor_pattern, content)
    
    # 收集文件的其他信息
    file_info = {
        'size': os.path.getsize(file_path),
        'line_count': len(content.splitlines()),
        'has_name': bool(re.search(r'<name>', content)),
        'has_description': bool(re.search(r'<description>', content)),
    }
    
    return weapon_matches, armor_matches, file_info

def find_xml_txt_files(root_dir):
    """
    递归查找指定目录及其子目录中的所有.xml和.txt文件
    返回包含文件路径和修改时间的元组列表
    """
    xml_txt_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.xml') or file.endswith('.txt'):
                full_path = os.path.join(root, file)
                mtime = os.path.getmtime(full_path)
                xml_txt_files.append((full_path, mtime))
    return xml_txt_files

def process_files(file_paths_with_time):
    """
    处理多个文件并输出结果
    只输出包含至少一个equipment id的文件
    """
    valid_files = []
    skipped_count = 0
    
    print("正在分析文件内容...")
    
    for file_path, mtime in file_paths_with_time:
        if not os.path.isfile(file_path):
            print(f"文件不存在: {file_path}", file=sys.stderr)
            continue
            
        weapon_ids, armor_ids, file_info = extract_equipment_ids_and_info(file_path)
        
        if weapon_ids or armor_ids:
            filename = os.path.splitext(os.path.basename(file_path))[0]
            
            weapon_str = ",".join(weapon_ids) if weapon_ids else ""
            armor_str = ",".join(armor_ids) if armor_ids else ""
            
            valid_files.append((filename, weapon_str, armor_str, mtime, file_path, file_info))
        else:
            skipped_count += 1
    
    valid_files.sort(key=lambda x: x[3], reverse=True)
    
    if valid_files:
        print(f"\n{common.Colors.YELLOW}文件名{common.Colors.RESET} {common.Colors.RED}weapon_ids{common.Colors.RESET} {common.Colors.CYAN}armor_ids{common.Colors.RESET}")
        print("-" * 60)
        
        for filename, weapon_str, armor_str, mtime, file_path, file_info in valid_files:
            colored_filename = f"{common.Colors.YELLOW}{filename}{common.Colors.RESET}"
            colored_weapon = f"{common.Colors.RED}{weapon_str}{common.Colors.RESET}" if weapon_str else ""
            colored_armor = f"{common.Colors.CYAN}{armor_str}{common.Colors.RESET}" if armor_str else ""
            
            print(f"{colored_filename} {colored_weapon} {colored_armor}")
        
        print(f"\n共找到 {len(valid_files)} 个包含装备ID的文件")
        if skipped_count > 0:
            print(f"已忽略 {skipped_count} 个未找到装备ID的文件")
            
        oldest = datetime.fromtimestamp(min([f[3] for f in valid_files]))
        newest = datetime.fromtimestamp(max([f[3] for f in valid_files]))
        print(f"文件时间范围: {oldest.strftime('%Y-%m-%d %H:%M')} 到 {newest.strftime('%Y-%m-%d %H:%M')}")
        
        single_letter_files = [f for f in valid_files if len(f[0]) == 1]
        if single_letter_files:
            print(f"\n{common.Colors.YELLOW}单字母文件详细信息:{common.Colors.RESET}")
            for filename, weapon_str, armor_str, mtime, file_path, file_info in single_letter_files:
                print(f"\n文件: {filename}")
                print(f"  路径: {file_path}")
                print(f"  大小: {file_info['size']} 字节")
                print(f"  行数: {file_info['line_count']}")
                print(f"  包含名称标签: {'是' if file_info['has_name'] else '否'}")
                print(f"  包含描述标签: {'是' if file_info['has_description'] else '否'}")
                print(f"  武器ID: {weapon_str}")
                print(f"  护甲ID: {armor_str}")
    else:
        print("未在任何文件中找到装备ID")

def main():
    """
    主函数 - 支持命令行参数和递归搜索
    """
    default_root = common.get_search_root_from_config()
    
    if len(sys.argv) > 1:
        file_paths_with_time = []
        for arg in sys.argv[1:]:
            if os.path.isdir(arg):
                file_paths_with_time.extend(find_xml_txt_files(arg))
            elif os.path.isfile(arg):
                mtime = os.path.getmtime(arg)
                file_paths_with_time.append((arg, mtime))
            else:
                print(f"路径不存在: {arg}", file=sys.stderr)
    else:
        search_dir = default_root
        print(f"正在递归搜索: {search_dir}")
        file_paths_with_time = find_xml_txt_files(search_dir)
    
    if not file_paths_with_time:
        print("未找到任何.xml或.txt文件")
        return
    
    print(f"扫描到 {len(file_paths_with_time)} 个文件")
    process_files(file_paths_with_time)

if __name__ == "__main__":
    main()