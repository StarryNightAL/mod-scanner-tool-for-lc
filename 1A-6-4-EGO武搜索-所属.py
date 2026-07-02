import os
import re
import sys
from datetime import datetime
import common   # 导入公共模块

def extract_weapon_info(file_path, root_path):
    """从文件中提取weapon信息"""
    weapons = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
        weapon_pattern = r'<equipment\s+id="([^"]*)"\s+type="weapon">(.*?)</equipment>'
        weapon_matches = re.findall(weapon_pattern, content, re.DOTALL | re.IGNORECASE)
        
        mod_folder, mod_time, mod_folder_path = common.get_mod_folder_and_time(file_path, root_path)
        print(f"\n{'#'*60}")
        print(f"处理文件: {file_path}")
        print(f"模组: {mod_folder}")
        print(f"找到 {len(weapon_matches)} 个武器")
        print(f"{'#'*60}")
        
        short_mod_name = mod_folder[:15] if mod_folder else "Unknown"
        localization_dir = common.find_localization_directory(mod_folder_path, 'cn') if mod_folder_path else None
        
        for weapon_id, weapon_content in weapon_matches:
            print(f"\n--- 处理武器ID: {weapon_id} ---")
            range_match = re.search(r'<range>([^<]*)</range>', weapon_content, re.IGNORECASE)
            attack_speed_match = re.search(r'<attackSpeed>([^<]*)</attackSpeed>', weapon_content, re.IGNORECASE)
            grade_match = re.search(r'<grade>([^<]*)</grade>', weapon_content, re.IGNORECASE)
            name_match = re.search(r'<name>([^<]*)</name>', weapon_content, re.IGNORECASE)
            
            range_value = range_match.group(1).strip() if range_match else "N/A"
            attack_speed_value = attack_speed_match.group(1).strip() if attack_speed_match else "N/A"
            grade_value = grade_match.group(1).strip() if grade_match else "N/A"
            name_id = name_match.group(1).strip() if name_match else "N/A"
            
            print(f"武器基本信息 - ID: {weapon_id}, name_id: {name_id}, grade: {grade_value}")
            mapped_grade = common.map_grade(grade_value)
            
            # 使用 common 统一接口获取研发成本和所属
            equipment_info = common.get_equipment_details(weapon_id, mod_folder_path)
            research_cost = equipment_info["cost"]
            belongs_to = equipment_info["belongs_to"]
            
            weapon_name = name_id
            if name_id != "N/A" and localization_dir:
                print(f"调试: 尝试解析名称ID: {name_id}")
                parsed_name = common.parse_name_from_xmls(name_id, localization_dir, debug=True)
                if parsed_name:
                    weapon_name = parsed_name
                    print(f"调试: 解析成功: {name_id} -> {parsed_name}")
                else:
                    print(f"调试: 解析失败: 未找到名称 '{name_id}'")
            elif name_id != "N/A":
                print(f"调试: XML目录不存在，无法解析名称")
            
            mod_time_str = common.format_mod_time(mod_time)
            
            weapons.append({
                'id': weapon_id.strip(),
                'name': weapon_name,
                'range': range_value,
                'attackSpeed': attack_speed_value,
                'grade': mapped_grade,
                'research_cost': research_cost,
                'belongs_to': belongs_to,
                'mod_folder': short_mod_name,
                'mod_time': mod_time,
                'mod_time_str': mod_time_str,
                'name_id': name_id
            })
            
    except Exception as e:
        print(f"错误: 提取武器信息时发生错误: {e}")
    
    return weapons

def main():
    root_dir = common.get_search_root_from_config()
    real_root_dir = common.resolve_symlink(root_dir)
    
    print(f"原始目录: {root_dir}")
    print(f"真实目录: {real_root_dir}")
    print("正在搜索武器信息...")
    print("仅处理 .txt 和 .xml 文件，跳过 BaseEquipment.txt")
    print("将从Equipment/xmls/cn目录解析武器名称")
    print("从Creature/Creatures/*_stat.txt文件提取研发所需cost")
    print("追踪武器所属生物信息")
    print("=" * 130)
    
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
    
    print(f"\n{'='*60}")
    print(f"处理了 {processed_files} 个文件，找到 {len(all_weapons)} 个武器")
    print(f"{'='*60}")
    print()
    
    if not all_weapons:
        print("在指定文件类型中未找到武器。")
        return
    
    all_weapons.sort(key=lambda x: (x['mod_time'] if x['mod_time'] is not None else float('inf'), x['mod_folder']))
    
    mod_header = common.pad_text("模组", 20)
    time_header = common.pad_text("修改时间", 12)
    id_header = common.pad_text("ID", 15)
    name_header = common.pad_text("武器名称", 25)
    belongs_header = common.pad_text("所属", 20)
    grade_header = common.pad_text("等级", 8)
    research_header = common.pad_text("研发所需", 12)
    
    print(f"{mod_header}{time_header}{id_header}{name_header}{belongs_header}{grade_header}{research_header}")
    print("-" * 120)
    
    for weapon in all_weapons:
        mod_field = common.pad_text(weapon['mod_folder'], 20)
        time_field = common.pad_text(weapon['mod_time_str'], 12)
        id_field = common.pad_text(weapon['id'], 15)
        name_field = common.pad_text(weapon['name'], 25)
        belongs_field = common.pad_text(weapon['belongs_to'], 20)
        grade_field = common.pad_text(weapon['grade'], 8)
        research_field = common.pad_text(weapon['research_cost'], 12)
        
        print(f"{mod_field}{time_field}{id_field}{name_field}{belongs_field}{grade_field}{research_field}")

if __name__ == "__main__":
    main()