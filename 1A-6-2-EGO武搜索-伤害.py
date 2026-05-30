import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
import common   # 导入公共模块

# 注意：以下两个函数是特有路径 "Equipment/xmls/cn"，与common不同，保留
def find_xmls_cn_directory(mod_folder_path):
    """在模组文件夹中查找Equipment/xmls/cn目录"""
    if not mod_folder_path or not os.path.exists(mod_folder_path):
        return None
    
    xmls_cn_path = os.path.join(mod_folder_path, "Equipment", "xmls", "cn")
    
    if os.path.exists(xmls_cn_path) and os.path.isdir(xmls_cn_path):
        return xmls_cn_path
    
    return None

def parse_name_from_xmls(name_id, xmls_cn_directory, debug=False):
    """从xmls/cn目录的.xml文件中解析name_id对应的文本"""
    if not xmls_cn_directory or not os.path.exists(xmls_cn_directory):
        if debug:
            print(f"调试: xmls/cn目录不存在: {xmls_cn_directory}")
        return None
    
    xml_files = []
    for file in os.listdir(xmls_cn_directory):
        if file.lower().endswith('.xml'):
            xml_files.append(os.path.join(xmls_cn_directory, file))
    
    if debug:
        print(f"调试: 在 {xmls_cn_directory} 中找到 {len(xml_files)} 个XML文件")
        for f in xml_files:
            print(f"  - {os.path.basename(f)}")
    
    if len(xml_files) == 0:
        if debug:
            print(f"调试: 在{xmls_cn_directory}中没有找到XML文件")
        return None
    elif len(xml_files) > 1:
        if "ColoredFixerMod-ReturnoftheRedmist" not in xmls_cn_directory:
            print(f"警告: 在{xmls_cn_directory}中发现多个.xml文件，跳过名称解析")
        return None
    
    xml_file = xml_files[0]
    
    if debug:
        print(f"调试: 解析XML文件: {xml_file}")
        print(f"调试: 查找ID: {name_id}")
    
    try:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            if debug:
                print(f"调试: XML根元素: {root.tag}")
            for elem in root.iter():
                elem_id = elem.get('id')
                if elem_id == name_id:
                    text = elem.text
                    if debug:
                        print(f"调试: 找到匹配元素 - 标签: {elem.tag}, ID: {elem_id}, 文本: {text}")
                    return text.strip() if text else None
        except ET.ParseError as e:
            if debug:
                print(f"调试: ElementTree解析失败: {e}")
        
        with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if debug:
            print(f"调试: XML文件大小: {len(content)} 字符")
            print(f"调试: XML文件前500字符:\n{content[:500]}")
        
        pattern = rf'<text\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</text>'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
            if debug:
                print(f"调试: 通过正则找到文本: {text}")
            return text
        
        pattern2 = rf'<[^>]+\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</[^>]+>'
        match2 = re.search(pattern2, content, re.DOTALL | re.IGNORECASE)
        if match2:
            text = match2.group(1).strip()
            if debug:
                print(f"调试: 通过宽泛正则找到文本: {text}")
            return text
            
        if debug:
            print(f"调试: 在XML文件中搜索包含'{name_id}'的行:")
            lines = content.split('\n')
            for i, line in enumerate(lines[:20]):
                if name_id in line:
                    print(f"  第{i+1}行: {line.strip()}")
            
    except Exception as e:
        if debug:
            print(f"调试: 解析XML时发生错误: {e}")
    
    if debug:
        print(f"调试: 未找到ID为'{name_id}'的文本")
    
    return None

def extract_damage_info(weapon_content):
    """提取伤害信息"""
    damage_matches = re.findall(r'<damage\s+type="([^"]*)"\s+min="([^"]*)"\s+max="([^"]*)"', weapon_content, re.IGNORECASE)
    
    if damage_matches:
        damage_type = damage_matches[0][0].strip()
        damage_min = damage_matches[0][1].strip()
        damage_max = damage_matches[0][2].strip()
        return damage_type, damage_min, damage_max
    
    damage_match = re.search(r'<damage\s+([^>]*)>', weapon_content, re.IGNORECASE)
    if damage_match:
        damage_attrs = damage_match.group(1)
        type_match = re.search(r'type\s*=\s*["\']([^"\']*)["\']', damage_attrs)
        min_match = re.search(r'min\s*=\s*["\']([^"\']*)["\']', damage_attrs)
        max_match = re.search(r'max\s*=\s*["\']([^"\']*)["\']', damage_attrs)
        
        damage_type = type_match.group(1).strip() if type_match else "N/A"
        damage_min = min_match.group(1).strip() if min_match else "N/A"
        damage_max = max_match.group(1).strip() if max_match else "N/A"
        return damage_type, damage_min, damage_max
    
    return "N/A", "N/A", "N/A"

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
        xmls_cn_directory = find_xmls_cn_directory(mod_folder_path) if mod_folder_path else None
        
        for weapon_id, weapon_content in weapon_matches:
            range_match = re.search(r'<range>([^<]*)</range>', weapon_content, re.IGNORECASE)
            attack_speed_match = re.search(r'<attackSpeed>([^<]*)</attackSpeed>', weapon_content, re.IGNORECASE)
            grade_match = re.search(r'<grade>([^<]*)</grade>', weapon_content, re.IGNORECASE)
            name_match = re.search(r'<name>([^<]*)</name>', weapon_content, re.IGNORECASE)
            
            range_value = range_match.group(1).strip() if range_match else "N/A"
            attack_speed_value = attack_speed_match.group(1).strip() if attack_speed_match else "N/A"
            grade_value = grade_match.group(1).strip() if grade_match else "N/A"
            name_id = name_match.group(1).strip() if name_match else "N/A"
            
            damage_type, damage_min, damage_max = extract_damage_info(weapon_content)
            mapped_grade = common.map_grade(grade_value)
            
            debug_mode = ("Depression" in mod_folder) or (name_id and re.search(r'_name', name_id))
            
            weapon_name = name_id
            if name_id != "N/A" and xmls_cn_directory:
                if debug_mode:
                    print(f"\n=== 调试 {mod_folder} ===")
                    print(f"武器ID: {weapon_id}")
                    print(f"名称ID: {name_id}")
                    print(f"XML目录: {xmls_cn_directory}")
                
                parsed_name = parse_name_from_xmls(name_id, xmls_cn_directory, debug=debug_mode)
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
                print(f"XML目录: 不存在")
            
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
                'damage_type': damage_type,
                'damage_min': damage_min,
                'damage_max': damage_max,
                'grade': mapped_grade,
                'mod_folder': short_mod_name,
                'mod_time': mod_time,
                'mod_time_str': mod_time_str,
                'name_id': name_id
            })
            
    except Exception as e:
        pass
    
    return weapons

def main():
    root_dir = common.get_search_root_from_config()
    real_root_dir = common.resolve_symlink(root_dir)
    
    print(f"原始目录: {root_dir}")
    print(f"真实目录: {real_root_dir}")
    print("正在搜索武器信息...")
    print("仅处理 .txt 和 .xml 文件，跳过 BaseEquipment.txt")
    print("将从Equipment/xmls/cn目录解析武器名称")
    print("提取伤害信息（类型、最小伤害、最大伤害）")
    print("注意: 已跳过ColoredFixerMod-ReturnoftheRedmist的多个XML文件警告")
    print("-" * 130)
    
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
    damage_type_header = common.pad_text("伤害类型", 12)
    damage_min_header = common.pad_text("最小伤害", 12)
    damage_max_header = common.pad_text("最大伤害", 12)
    
    print(f"{mod_header}{time_header}{id_header}{name_header}{grade_header}{damage_type_header}{damage_min_header}{damage_max_header}")
    print("-" * 130)
    
    for weapon in all_weapons:
        mod_field = common.pad_text(weapon['mod_folder'], 20)
        time_field = common.pad_text(weapon['mod_time_str'], 12)
        id_field = common.pad_text(weapon['id'], 15)
        name_field = common.pad_text(weapon['name'], 25)
        grade_field = common.pad_text(weapon['grade'], 8)
        damage_type_field = common.pad_text(weapon['damage_type'], 12)
        damage_min_field = common.pad_text(weapon['damage_min'], 12)
        damage_max_field = common.pad_text(weapon['damage_max'], 12)
        
        print(f"{mod_field}{time_field}{id_field}{name_field}{grade_field}{damage_type_field}{damage_min_field}{damage_max_field}")

if __name__ == "__main__":
    main()