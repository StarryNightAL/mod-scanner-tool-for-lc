import os
import re
import sys
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import common   # 导入公共模块

def main():
    root_dir = common.get_search_root_from_config()
    real_root_dir = common.resolve_symlink(root_dir)
    
    print(f"原始目录: {root_dir}")
    print(f"真实目录: {real_root_dir}")
    print("正在搜索武器信息...")
    print("仅处理 .txt 和 .xml 文件，跳过 BaseEquipment.txt")
    print("将从Equipment/xmls目录解析武器名称（优先cn，然后是en等语言）")
    print("-" * 120)
    
    all_weapons = []
    processed_files = 0
    
    for root, dirs, files in os.walk(real_root_dir, followlinks=True):
        if '.git' in dirs:
            dirs.remove('.git')
        
        for file in files:
            file_path = os.path.join(root, file)
            
            if common.should_process_file(file_path):
                weapons = extract_weapon_info(file_path, real_root_dir)
                if weapons:
                    all_weapons.extend(weapons)
                    processed_files += 1
    
    print(f"\n处理了 {processed_files} 个文件，找到 {len(all_weapons)} 个武器")
    print()
    
    if not all_weapons:
        print("在指定文件类型中未找到武器。")
        return
    
    all_weapons.sort(key=lambda x: (x['mod_time'] if x['mod_time'] is not None else float('inf'), x['mod_folder']))
    
    mod_header = common.pad_text("模组", 20)
    time_header = common.pad_text("修改时间", 12)
    id_header = common.pad_text("ID", 15)
    name_header = common.pad_text("武器名称", 25)
    grade_header = common.pad_text("等级", 8)
    attack_speed_header = common.pad_text("攻击速度", 12)
    range_header = common.pad_text("攻击距离", 8)
    
    print(f"{mod_header}{time_header}{id_header}{name_header}{grade_header}{attack_speed_header}{range_header}")
    print("-" * 120)
    
    for weapon in all_weapons:
        mod_field = common.pad_text(weapon['mod_folder'], 20)
        time_field = common.pad_text(weapon['mod_time_str'], 12)
        id_field = common.pad_text(weapon['id'], 15)
        name_field = common.pad_text(weapon['name'], 25)
        grade_field = common.pad_text(weapon['grade'], 8)
        attack_speed_field = common.pad_text(weapon['attackSpeed'], 12)
        range_field = common.pad_text(weapon['range'], 8)
        
        print(f"{mod_field}{time_field}{id_field}{name_field}{grade_field}{attack_speed_field}{range_field}")

def extract_weapon_info(file_path, root_path):
    """从文件中提取weapon信息"""
    weapons = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
        weapon_pattern = r'<equipment\s+id="([^"]*)"\s+type="weapon">(.*?)</equipment>'
        weapon_matches = re.findall(weapon_pattern, content, re.DOTALL | re.IGNORECASE)
        
        mod_folder, mod_time, mod_folder_path = common.get_mod_folder_and_time(file_path, root_path)
        short_mod_name = mod_folder[:15] if mod_folder else "Unknown"
        localization_directory = common.find_localization_directory(mod_folder_path, 'cn') if mod_folder_path else None
        
        for weapon_id, weapon_content in weapon_matches:
            range_match = re.search(r'<range>([^<]*)</range>', weapon_content, re.IGNORECASE)
            attack_speed_match = re.search(r'<attackSpeed>([^<]*)</attackSpeed>', weapon_content, re.IGNORECASE)
            grade_match = re.search(r'<grade>([^<]*)</grade>', weapon_content, re.IGNORECASE)
            name_match = re.search(r'<name>([^<]*)</name>', weapon_content, re.IGNORECASE)
            
            range_value = range_match.group(1).strip() if range_match else "N/A"
            attack_speed_value = attack_speed_match.group(1).strip() if attack_speed_match else "N/A"
            grade_value = grade_match.group(1).strip() if grade_match else "N/A"
            name_id = name_match.group(1).strip() if name_match else "N/A"
            
            mapped_grade = common.map_grade(grade_value)
            
            debug_mode = ("Depression" in mod_folder) or (name_id and re.search(r'_name', name_id))
            
            weapon_name = name_id
            if name_id != "N/A" and localization_directory:
                if debug_mode:
                    print(f"\n=== 调试 {mod_folder} ===")
                    print(f"武器ID: {weapon_id}")
                    print(f"名称ID: {name_id}")
                    print(f"本地化目录: {localization_directory}")
                
                parsed_name = common.parse_name_from_xmls(name_id, localization_directory, debug=debug_mode)
                if parsed_name:
                    weapon_name = parsed_name
                    if debug_mode:
                        print(f"解析成功: {name_id} -> {parsed_name}")
                elif debug_mode:
                    print(f"解析失败: 未找到名称 '{name_id}'")
            elif name_id != "N/A" and debug_mode:
                print(f"\n=== 调试 {mod_folder} ===")
                print(f"武器ID: {weapon_id}")
                print(f"名称ID: {name_id}")
                print(f"本地化目录: 不存在")
            
            mod_time_str = ""
            if mod_time:
                try:
                    mod_time_str = datetime.fromtimestamp(mod_time).strftime('%m-%d %H:%M')
                except:
                    mod_time_str = ""
            
            weapons.append({
                'id': weapon_id.strip(),
                'name': weapon_name,
                'range': range_value,
                'attackSpeed': attack_speed_value,
                'grade': mapped_grade,
                'mod_folder': short_mod_name,
                'mod_time': mod_time,
                'mod_time_str': mod_time_str,
                'name_id': name_id
            })
            
    except Exception as e:
        pass
    
    return weapons

if __name__ == "__main__":
    main()