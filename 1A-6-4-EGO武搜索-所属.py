import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
import configparser

def get_search_root_from_config(default_root=None):
    """从脚本所在目录的config.ini中读取target_scan_path，若失败则返回default_root"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    if os.path.isfile(config_path):
        try:
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            path = config.get('CORE', 'target_scan_path', fallback=None)
            if path:
                path = path.strip()
                # 相对路径转换为相对于脚本目录的绝对路径
                if not os.path.isabs(path):
                    path = os.path.join(script_dir, path)
                return path
        except Exception:
            pass
    return default_root if default_root is not None else os.getcwd()

# 定义等级映射
GRADE_MAPPING = {
    '1': 'ZAYIN',
    '2': 'TETH', 
    '3': 'HE',
    '4': 'WAW',
    '5': 'ALEPH'
}

def should_process_file(file_path):
    """判断是否应该处理该文件"""
    filename = os.path.basename(file_path)
    
    # 跳过 BaseEquipment.txt 文件
    if filename.lower() == "baseequipment.txt":
        return False
    
    # 只处理 .txt 和 .xml 文件
    ext = os.path.splitext(file_path)[1].lower()
    return ext in ('.txt', '.xml')

def map_grade(grade_value):
    """将数字等级映射为对应的名称"""
    # 先移除可能的空格
    grade_value = grade_value.strip() if grade_value else grade_value
    return GRADE_MAPPING.get(grade_value, grade_value)

def resolve_symlink(path):
    """解析符号链接，返回真实路径"""
    try:
        return os.path.realpath(path)
    except:
        return path

def get_mod_folder_and_time(file_path, root_path):
    """获取文件所属的模组文件夹和修改时间"""
    try:
        # 解析符号链接
        real_file_path = resolve_symlink(file_path)
        real_root_path = resolve_symlink(root_path)
        
        # 获取文件相对于根路径的相对路径
        try:
            rel_path = os.path.relpath(real_file_path, real_root_path)
        except ValueError:
            # 如果不在同一驱动器，尝试直接使用绝对路径
            rel_path = real_file_path
        
        # 分割相对路径，第一个部分应该是模组文件夹名
        path_parts = rel_path.split(os.sep)
        
        if len(path_parts) > 1 and path_parts[0] != '..' and path_parts[0] != '.':
            mod_folder_name = path_parts[0]
            mod_folder_path = os.path.join(real_root_path, mod_folder_name)
            
            # 获取模组文件夹的修改时间
            if os.path.exists(mod_folder_path):
                mod_time = os.path.getmtime(mod_folder_path)
                return mod_folder_name, mod_time, mod_folder_path
            else:
                return mod_folder_name, None, None
        else:
            # 如果文件直接在根路径下，没有模组文件夹
            return "Root", os.path.getmtime(real_file_path), real_root_path
            
    except (ValueError, OSError):
        # 如果无法获取相对路径或修改时间
        return "Unknown", None, None

def find_xmls_cn_directory(mod_folder_path):
    """在模组文件夹中查找Equipment/xmls/cn目录"""
    if not mod_folder_path or not os.path.exists(mod_folder_path):
        print(f"调试: 模组文件夹不存在: {mod_folder_path}")
        return None
    
    # 构造正确的路径: 模组文件夹/Equipment/xmls/cn
    xmls_cn_path = os.path.join(mod_folder_path, "Equipment", "xmls", "cn")
    
    print(f"调试: 尝试查找XML目录: {xmls_cn_path}")
    
    if os.path.exists(xmls_cn_path) and os.path.isdir(xmls_cn_path):
        print(f"调试: 找到XML目录: {xmls_cn_path}")
        return xmls_cn_path
    else:
        print(f"调试: XML目录不存在: {xmls_cn_path}")
    
    return None

def parse_name_from_xmls(name_id, xmls_cn_directory, debug=False):
    """从xmls/cn目录的.xml文件中解析name_id对应的文本"""
    if not xmls_cn_directory or not os.path.exists(xmls_cn_directory):
        print(f"调试: xmls/cn目录不存在: {xmls_cn_directory}")
        return None
    
    # 收集xmls/cn目录下所有.xml文件
    xml_files = []
    for file in os.listdir(xmls_cn_directory):
        if file.lower().endswith('.xml'):
            xml_files.append(os.path.join(xmls_cn_directory, file))
    
    print(f"调试: 在 {xmls_cn_directory} 中找到 {len(xml_files)} 个XML文件")
    for f in xml_files:
        print(f"  - {os.path.basename(f)}")
    
    # 检查.xml文件数量
    if len(xml_files) == 0:
        print(f"调试: 在{xmls_cn_directory}中没有找到XML文件")
        return None
    elif len(xml_files) > 1:
        # 检查是否包含ColoredFixerMod-ReturnoftheRedmist，如果是则跳过警告
        if "ColoredFixerMod-ReturnoftheRedmist" not in xmls_cn_directory:
            print(f"警告: 在{xmls_cn_directory}中发现多个.xml文件，跳过名称解析")
        return None
    
    # 只有一个.xml文件，解析它
    xml_file = xml_files[0]
    
    print(f"调试: 解析XML文件: {xml_file}")
    print(f"调试: 查找ID: {name_id}")
    
    try:
        # 方法1: 使用ElementTree解析
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            print(f"调试: XML根元素: {root.tag}")
            
            # 查找所有元素
            for elem in root.iter():
                elem_id = elem.get('id')
                if elem_id == name_id:
                    text = elem.text
                    print(f"调试: 找到匹配元素 - 标签: {elem.tag}, ID: {elem_id}, 文本: {text}")
                    return text.strip() if text else None
        except ET.ParseError as e:
            print(f"调试: ElementTree解析失败: {e}")
        
        # 方法2: 使用正则表达式查找
        with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        print(f"调试: XML文件大小: {len(content)} 字符")
        
        # 匹配格式: <text id="ID">文本</text>
        pattern = rf'<text\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</text>'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            text = match.group(1).strip()
            print(f"调试: 通过正则找到文本: {text}")
            return text
        
        # 方法3: 尝试更宽泛的匹配
        pattern2 = rf'<[^>]+\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</[^>]+>'
        match2 = re.search(pattern2, content, re.DOTALL | re.IGNORECASE)
        
        if match2:
            text = match2.group(1).strip()
            print(f"调试: 通过宽泛正则找到文本: {text}")
            return text
            
        # 尝试查找是否有相似的内容
        print(f"调试: 在XML文件中搜索包含'{name_id}'的行:")
        lines = content.split('\n')
        found = False
        for i, line in enumerate(lines[:50]):  # 只查看前50行
            if name_id in line:
                print(f"  第{i+1}行: {line.strip()}")
                found = True
        if not found:
            print(f"  未找到包含'{name_id}'的行")
            
    except Exception as e:
        print(f"调试: 解析XML时发生错误: {e}")
    
    print(f"调试: 未找到ID为'{name_id}'的文本")
    
    return None

def find_stat_files(mod_folder_path):
    """在模组文件夹中查找Creature/Creatures/*_stat.txt文件"""
    if not mod_folder_path or not os.path.exists(mod_folder_path):
        print(f"调试: 模组文件夹不存在: {mod_folder_path}")
        return []
    
    # 构造Creature/Creatures目录路径
    creature_path = os.path.join(mod_folder_path, "Creature", "Creatures")
    
    print(f"调试: 尝试查找Creature/Creatures目录: {creature_path}")
    
    if not os.path.exists(creature_path):
        print(f"调试: Creature/Creatures目录不存在: {creature_path}")
        return []
    
    # 查找所有_stat.txt文件
    stat_files = []
    print(f"调试: 在{creature_path}中搜索_stat.txt文件")
    
    # 首先检查根目录
    for file in os.listdir(creature_path):
        if file.lower().endswith('_stat.txt'):
            file_path = os.path.join(creature_path, file)
            stat_files.append(file_path)
            print(f"调试: 找到stat文件: {file_path}")
    
    # 然后递归搜索子目录
    for root, dirs, files in os.walk(creature_path):
        # 跳过当前目录（已处理）
        if root == creature_path:
            continue
        for file in files:
            if file.lower().endswith('_stat.txt'):
                file_path = os.path.join(root, file)
                stat_files.append(file_path)
                print(f"调试: 在子目录找到stat文件: {file_path}")
    
    print(f"调试: 总共找到 {len(stat_files)} 个stat文件")
    return stat_files

def parse_stat_file_for_equipment(stat_file):
    """从_stat.txt文件中提取equipment信息和script信息"""
    equipment_dict = {}
    script_name = None
    
    print(f"调试: 解析stat文件: {stat_file}")
    
    try:
        with open(stat_file, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        print(f"调试: stat文件大小: {len(content)} 字符")
        
        # 提取script标签 - 多种可能格式
        script_patterns = [
            r'<script>([^<]+)</script>',
            r'<script\s+[^>]*>([^<]+)</script>',
            r'script\s*=\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in script_patterns:
            script_match = re.search(pattern, content, re.IGNORECASE)
            if script_match:
                script_name = script_match.group(1).strip()
                print(f"调试: 找到script: {script_name}")
                break
        
        if not script_name:
            print(f"调试: 未找到script标签")
        
        # 使用正则表达式匹配<equipment>标签
        # 匹配格式: <equipment level="4" cost="74" equipId="440001" />
        # 也尝试其他可能的属性顺序
        equipment_patterns = [
            r'<equipment\s+[^>]*?\s+equipId\s*=\s*["\']([^"\']*)["\'][^>]*?>',
            r'<equipment\s+[^>]*?\s+equipid\s*=\s*["\']([^"\']*)["\'][^>]*?>',  # 小写equipid
            r'equipId\s*=\s*["\']([^"\']*)["\']'  # 更宽松的匹配
        ]
        
        equipment_matches = []
        for pattern in equipment_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                equipment_matches = matches
                print(f"调试: 使用模式'{pattern}'找到{len(matches)}个equipment匹配")
                break
        
        if not equipment_matches:
            print(f"调试: 未找到任何equipment标签")
            return equipment_dict
        
        # 对于每个匹配，提取level, cost, equipId
        for equip_id in equipment_matches:
            # 为这个equipId查找完整的标签来提取cost
            pattern = rf'<equipment\s+[^>]*?\s+equipId\s*=\s*["\']{re.escape(equip_id)}["\'][^>]*?>'
            match = re.search(pattern, content, re.IGNORECASE)
            
            if not match:
                # 尝试小写equipid
                pattern = rf'<equipment\s+[^>]*?\s+equipid\s*=\s*["\']{re.escape(equip_id)}["\'][^>]*?>'
                match = re.search(pattern, content, re.IGNORECASE)
            
            if match:
                equipment_tag = match.group(0)
                print(f"调试: 找到equipment标签: {equipment_tag}")
                
                # 提取cost
                cost_match = re.search(r'cost\s*=\s*["\']([^"\']*)["\']', equipment_tag, re.IGNORECASE)
                cost = cost_match.group(1) if cost_match else "N/A"
                
                # 提取level（可选）
                level_match = re.search(r'level\s*=\s*["\']([^"\']*)["\']', equipment_tag, re.IGNORECASE)
                level = level_match.group(1) if level_match else "N/A"
                
                equipment_dict[equip_id.strip()] = {
                    'cost': cost.strip(),
                    'level': level.strip(),
                    'script_name': script_name
                }
                
                print(f"调试: 提取equipment信息 - ID: {equip_id}, cost: {cost}, level: {level}, script: {script_name}")
            else:
                print(f"调试: 无法找到equipId '{equip_id}' 的完整标签")
                
    except Exception as e:
        print(f"调试: 解析stat文件时发生错误: {e}")
    
    print(f"调试: 从stat文件提取到 {len(equipment_dict)} 个equipment条目")
    return equipment_dict

def get_creature_id_from_creature_list(script_name, mod_folder_path):
    """从Creature/CreatureList/*.txt文件中查找creature ID"""
    if not script_name or not mod_folder_path:
        print(f"调试: script_name或mod_folder_path为空")
        return None
    
    # 构造Creature/CreatureList目录路径
    creature_list_path = os.path.join(mod_folder_path, "Creature", "CreatureList")
    
    print(f"调试: 尝试查找CreatureList目录: {creature_list_path}")
    
    if not os.path.exists(creature_list_path):
        print(f"调试: Creature/CreatureList目录不存在: {creature_list_path}")
        return None
    
    # 查找所有.txt文件
    creature_list_files = []
    for file in os.listdir(creature_list_path):
        if file.lower().endswith('.txt'):
            creature_list_files.append(os.path.join(creature_list_path, file))
    
    print(f"调试: 在CreatureList目录中找到 {len(creature_list_files)} 个.txt文件")
    
    if not creature_list_files:
        print(f"调试: CreatureList目录中没有.txt文件")
        return None
    
    # 遍历所有文件查找匹配的creature
    for file_path in creature_list_files:
        try:
            print(f"调试: 检查文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            print(f"调试: 文件大小: {len(content)} 字符")
            
            # 查找包含指定script_name的creature标签
            # 格式: <creature name="Oktavia" src="Oktavia" id="158160">
            pattern = rf'<creature\s+[^>]*?\s+name\s*=\s*["\']{re.escape(script_name)}["\'][^>]*?>'
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            print(f"调试: 找到 {len(matches)} 个匹配的creature标签")
            
            for i, match in enumerate(matches):
                print(f"调试: 匹配 {i+1}: {match}")
                # 提取id
                id_match = re.search(r'id\s*=\s*["\']([^"\']*)["\']', match)
                if id_match:
                    creature_id = id_match.group(1).strip()
                    print(f"调试: 找到creature ID: {creature_id}")
                    return creature_id
                else:
                    print(f"调试: 未在标签中找到id属性")
        
        except Exception as e:
            print(f"调试: 读取文件{file_path}时发生错误: {e}")
            continue
    
    print(f"调试: 未找到name为'{script_name}'的creature标签")
    
    # 尝试在文件内容中搜索script_name
    print(f"调试: 尝试在文件内容中搜索'{script_name}'...")
    for file_path in creature_list_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            if script_name in content:
                print(f"调试: 在文件 {file_path} 中找到 '{script_name}'")
                # 尝试提取附近的标签
                lines = content.split('\n')
                for j, line in enumerate(lines):
                    if script_name in line:
                        print(f"调试: 第{j+1}行: {line.strip()}")
        except:
            continue
    
    return None

def get_creature_name_from_creature_info(creature_id, mod_folder_path):
    """从Creature/CreatureInfo/cn/*.txt或*.xml文件中查找creature名称"""
    if not creature_id or not mod_folder_path:
        print(f"调试: creature_id或mod_folder_path为空")
        return None
    
    # 构造Creature/CreatureInfo/cn目录路径
    creature_info_path = os.path.join(mod_folder_path, "Creature", "CreatureInfo", "cn")
    
    print(f"调试: 尝试查找CreatureInfo/cn目录: {creature_info_path}")
    
    if not os.path.exists(creature_info_path):
        print(f"调试: Creature/CreatureInfo/cn目录不存在: {creature_info_path}")
        return None
    
    # 查找所有.txt和.xml文件
    creature_info_files = []
    for file in os.listdir(creature_info_path):
        if file.lower().endswith('.txt') or file.lower().endswith('.xml'):
            creature_info_files.append(os.path.join(creature_info_path, file))
    
    print(f"调试: 在CreatureInfo/cn目录中找到 {len(creature_info_files)} 个文件")
    
    if not creature_info_files:
        print(f"调试: CreatureInfo/cn目录中没有.txt或.xml文件")
        return None
    
    # 遍历所有文件查找匹配的info
    for file_path in creature_info_files:
        try:
            print(f"调试: 检查文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            print(f"调试: 文件大小: {len(content)} 字符")
            
            # 查找匹配的info标签
            pattern = rf'<info\s+id\s*=\s*["\']{re.escape(creature_id)}["\'][^>]*?>(.*?)</info>'
            info_matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            
            print(f"调试: 找到 {len(info_matches)} 个匹配的info标签")
            
            if info_matches:
                # 取最后一个info块
                info_content = info_matches[-1]
                print(f"调试: 最后一个info块内容（前500字符）:\n{info_content[:500]}")
                
                # 在info块中查找所有的name标签
                name_pattern = r'<name\s+openLevel\s*=\s*["\'][^"\']*["\'][^>]*?>(.*?)</name>'
                name_matches = re.findall(name_pattern, info_content, re.DOTALL | re.IGNORECASE)
                
                print(f"调试: 在info块中找到 {len(name_matches)} 个name标签")
                
                if name_matches:
                    # 取最后一个name标签的文本内容
                    last_name_text = name_matches[-1].strip()
                    # 清理文本，移除多余空格和换行
                    last_name_text = re.sub(r'\s+', ' ', last_name_text)
                    print(f"调试: 最后一个name标签文本: '{last_name_text}'")
                    return last_name_text
                else:
                    print(f"调试: info块中没有找到name标签")
                    # 尝试其他可能的name标签格式
                    alt_name_patterns = [
                        r'<name[^>]*?>(.*?)</name>',  # 更宽松的name标签
                        r'<Name[^>]*?>(.*?)</Name>',  # 大写Name
                    ]
                    for alt_pattern in alt_name_patterns:
                        alt_matches = re.findall(alt_pattern, info_content, re.DOTALL | re.IGNORECASE)
                        if alt_matches:
                            print(f"调试: 使用备用模式找到 {len(alt_matches)} 个name标签")
                            last_name_text = alt_matches[-1].strip()
                            last_name_text = re.sub(r'\s+', ' ', last_name_text)
                            print(f"调试: 备用name标签文本: '{last_name_text}'")
                            return last_name_text
            else:
                print(f"调试: 未找到id为'{creature_id}'的info标签")
                # 尝试搜索creature_id
                if creature_id in content:
                    print(f"调试: 在文件中找到creature_id '{creature_id}'")
                    lines = content.split('\n')
                    for j, line in enumerate(lines):
                        if creature_id in line:
                            print(f"调试: 第{j+1}行: {line.strip()}")
        
        except Exception as e:
            print(f"调试: 读取文件{file_path}时发生错误: {e}")
            continue
    
    print(f"调试: 在所有文件中都未找到id为'{creature_id}'的info标签")
    return None

def get_equipment_info(weapon_id, mod_folder_path):
    """获取武器的研发所需cost和所属creature名称"""
    print(f"\n{'='*60}")
    print(f"调试: 开始处理武器ID: {weapon_id}")
    print(f"调试: 模组文件夹: {mod_folder_path}")
    
    if not mod_folder_path:
        print(f"调试: 模组文件夹路径不存在")
        print(f"{'='*60}")
        return {"cost": "N/A", "belongs_to": "N/A"}
    
    # 查找_stat.txt文件
    stat_files = find_stat_files(mod_folder_path)
    
    if not stat_files:
        print(f"调试: 未找到stat文件")
        print(f"{'='*60}")
        return {"cost": "N/A", "belongs_to": "N/A"}
    
    # 遍历所有_stat.txt文件，查找匹配的equipId
    for stat_file in stat_files:
        equipment_dict = parse_stat_file_for_equipment(stat_file)
        
        print(f"调试: 在文件{stat_file}中找到 {len(equipment_dict)} 个equipment条目")
        
        if weapon_id in equipment_dict:
            equipment_info = equipment_dict[weapon_id]
            cost = equipment_info['cost']
            script_name = equipment_info.get('script_name')
            
            print(f"调试: 匹配到武器ID {weapon_id}")
            print(f"调试: cost: {cost}, script_name: {script_name}")
            
            belongs_to = "N/A"
            
            # 如果找到script_name，尝试获取creature名称
            if script_name:
                print(f"调试: 开始根据script_name '{script_name}' 查找creature")
                # 第一步：从CreatureList获取creature id
                creature_id = get_creature_id_from_creature_list(script_name, mod_folder_path)
                
                if creature_id:
                    print(f"调试: 获取到的creature_id: {creature_id}")
                    
                    # 第二步：从CreatureInfo获取creature名称
                    creature_name = get_creature_name_from_creature_info(creature_id, mod_folder_path)
                    
                    if creature_name:
                        print(f"调试: 获取到的creature_name: {creature_name}")
                        belongs_to = creature_name
                    else:
                        print(f"调试: 未找到creature_name")
                else:
                    print(f"调试: 未找到creature_id")
            else:
                print(f"调试: 未找到script_name")
            
            print(f"调试: 处理完成 - cost: {cost}, belongs_to: {belongs_to}")
            print(f"{'='*60}")
            return {"cost": cost, "belongs_to": belongs_to}
        else:
            print(f"调试: 武器ID {weapon_id} 在该stat文件中未找到匹配")
    
    print(f"调试: 在所有stat文件中均未找到武器ID {weapon_id}")
    print(f"{'='*60}")
    return {"cost": "N/A", "belongs_to": "N/A"}

def extract_weapon_info(file_path, root_path):
    """从文件中提取weapon信息"""
    weapons = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
        # 使用正则表达式匹配weapon块
        weapon_pattern = r'<equipment\s+id="([^"]*)"\s+type="weapon">(.*?)</equipment>'
        weapon_matches = re.findall(weapon_pattern, content, re.DOTALL | re.IGNORECASE)
        
        # 获取模组文件夹和修改时间
        mod_folder, mod_time, mod_folder_path = get_mod_folder_and_time(file_path, root_path)
        
        print(f"\n{'#'*60}")
        print(f"处理文件: {file_path}")
        print(f"模组: {mod_folder}")
        print(f"找到 {len(weapon_matches)} 个武器")
        print(f"{'#'*60}")
        
        # 截取模组文件夹名前15位
        short_mod_name = mod_folder[:15] if mod_folder else "Unknown"
        
        # 查找Equipment/xmls/cn目录
        xmls_cn_directory = find_xmls_cn_directory(mod_folder_path) if mod_folder_path else None
        
        for weapon_id, weapon_content in weapon_matches:
            print(f"\n--- 处理武器ID: {weapon_id} ---")
            
            # 在weapon内容中查找range, attackSpeed, grade, name
            range_match = re.search(r'<range>([^<]*)</range>', weapon_content, re.IGNORECASE)
            attack_speed_match = re.search(r'<attackSpeed>([^<]*)</attackSpeed>', weapon_content, re.IGNORECASE)
            grade_match = re.search(r'<grade>([^<]*)</grade>', weapon_content, re.IGNORECASE)
            name_match = re.search(r'<name>([^<]*)</name>', weapon_content, re.IGNORECASE)
            
            range_value = range_match.group(1).strip() if range_match else "N/A"
            attack_speed_value = attack_speed_match.group(1).strip() if attack_speed_match else "N/A"
            grade_value = grade_match.group(1).strip() if grade_match else "N/A"
            name_id = name_match.group(1).strip() if name_match else "N/A"
            
            print(f"武器基本信息 - ID: {weapon_id}, name_id: {name_id}, grade: {grade_value}")
            
            # 映射等级
            mapped_grade = map_grade(grade_value)
            
            # 获取研发所需cost和所属creature
            equipment_info = get_equipment_info(weapon_id, mod_folder_path)
            research_cost = equipment_info["cost"]
            belongs_to = equipment_info["belongs_to"]
            
            # 从xmls/cn目录解析name
            weapon_name = name_id  # 默认使用name_id
            if name_id != "N/A" and xmls_cn_directory:
                print(f"调试: 尝试解析名称ID: {name_id}")
                parsed_name = parse_name_from_xmls(name_id, xmls_cn_directory, debug=True)
                if parsed_name:
                    weapon_name = parsed_name
                    print(f"调试: 解析成功: {name_id} -> {parsed_name}")
                else:
                    print(f"调试: 解析失败: 未找到名称 '{name_id}'")
            elif name_id != "N/A":
                print(f"调试: XML目录不存在，无法解析名称")
            
            # 格式化修改时间
            mod_time_str = ""
            if mod_time:
                try:
                    mod_time_str = datetime.fromtimestamp(mod_time).strftime('%m-%d %H:%M')
                except:
                    mod_time_str = ""
            
            weapons.append({
                'id': weapon_id.strip(),
                'name': weapon_name,
                'range': range_value,  # 保留但不显示
                'attackSpeed': attack_speed_value,  # 保留但不显示
                'grade': mapped_grade,
                'research_cost': research_cost,  # 研发所需cost
                'belongs_to': belongs_to,  # 所属creature
                'mod_folder': short_mod_name,
                'mod_time': mod_time,
                'mod_time_str': mod_time_str,
                'name_id': name_id  # 保留原始的name_id用于调试
            })
            
    except Exception as e:
        print(f"错误: 提取武器信息时发生错误: {e}")
    
    return weapons

def get_display_width(text):
    """计算字符串在控制台中的显示宽度"""
    if text is None:
        return 0
        
    width = 0
    for char in str(text):
        # 中文字符通常占2个英文字符宽度
        if '\u4e00' <= char <= '\u9fff':
            width += 2
        else:
            width += 1
    return width

def pad_text(text, width):
    """将文本填充到指定宽度，考虑中英文字符宽度差异"""
    if text is None:
        text = ""
    text = str(text)
    current_width = get_display_width(text)
    if current_width >= width:
        return text
    return text + ' ' * (width - current_width)

def main():
    # 获取当前目录并解析符号链接
    root_dir = get_search_root_from_config()
    real_root_dir = resolve_symlink(root_dir)
    
    print(f"原始目录: {root_dir}")
    print(f"真实目录: {real_root_dir}")
    print("正在搜索武器信息...")
    print("仅处理 .txt 和 .xml 文件，跳过 BaseEquipment.txt")
    print("将从Equipment/xmls/cn目录解析武器名称")
    print("从Creature/Creatures/*_stat.txt文件提取研发所需cost")
    print("追踪武器所属生物信息")
    print("注意: 已跳过ColoredFixerMod-ReturnoftheRedmist的多个XML文件警告")
    print("=" * 130)
    
    all_weapons = []
    processed_files = 0
    
    # 递归遍历所有文件和子目录，跟随符号链接
    for root, dirs, files in os.walk(real_root_dir, followlinks=True):
        # 跳过 .git 目录以提高性能
        if '.git' in dirs:
            dirs.remove('.git')
        
        for file in files:
            file_path = os.path.join(root, file)
            
            # 检查是否应该处理该文件
            if should_process_file(file_path):
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
    
    # 按模组文件夹修改时间排序（越早修改的越靠前）
    all_weapons.sort(key=lambda x: (x['mod_time'] if x['mod_time'] is not None else float('inf'), x['mod_folder']))
    
    # 打印表头 - 更新为包含研发所需和所属列
    mod_header = pad_text("模组", 20)
    time_header = pad_text("修改时间", 12)
    id_header = pad_text("ID", 15)
    name_header = pad_text("武器名称", 25)
    belongs_header = pad_text("所属", 20)
    grade_header = pad_text("等级", 8)
    research_header = pad_text("研发所需", 12)
    
    print(f"{mod_header}{time_header}{id_header}{name_header}{belongs_header}{grade_header}{research_header}")
    print("-" * 120)
    
    # 打印每个weapon的信息
    for weapon in all_weapons:
        mod_field = pad_text(weapon['mod_folder'], 20)
        time_field = pad_text(weapon['mod_time_str'], 12)
        id_field = pad_text(weapon['id'], 15)
        name_field = pad_text(weapon['name'], 25)
        belongs_field = pad_text(weapon['belongs_to'], 20)
        grade_field = pad_text(weapon['grade'], 8)
        research_field = pad_text(weapon['research_cost'], 12)
        
        print(f"{mod_field}{time_field}{id_field}{name_field}{belongs_field}{grade_field}{research_field}")

if __name__ == "__main__":
    main()