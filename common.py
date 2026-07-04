import os
import re
import sys
import configparser
import inspect
from datetime import datetime

# ==================== 1. 配置加载 ====================
def get_search_root_from_config(default_root=None):
    """从脚本所在目录的config.ini中读取target_scan_path，若失败则返回default_root"""
    # 获取调用者的文件路径
    caller_frame = inspect.currentframe().f_back
    caller_file = caller_frame.f_globals.get('__file__')
    if caller_file:
        script_dir = os.path.dirname(os.path.abspath(caller_file))
    else:
        # fallback: 使用当前工作目录
        script_dir = os.getcwd()

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

# ==================== 2. 等级映射 ====================
# 定义等级映射
GRADE_MAPPING = {
    '1': 'ZAYIN',
    '2': 'TETH',
    '3': 'HE',
    '4': 'WAW',
    '5': 'ALEPH'
}

def map_grade(grade_value):
    """将数字等级映射为对应的名称"""
    grade_value = str(grade_value).strip() if grade_value else ''
    return GRADE_MAPPING.get(grade_value, grade_value)

# ==================== 3. 文件处理 ====================
def should_process_file(file_path):
    """判断是否应该处理该文件"""
    filename = os.path.basename(file_path)
    
    # 特殊处理 BaseEquipment.txt
    if filename.lower() == "baseequipment.txt":
        # 获取调用者脚本目录下的 config.ini
        caller_frame = inspect.currentframe().f_back
        caller_file = caller_frame.f_globals.get('__file__')
        if caller_file:
            script_dir = os.path.dirname(os.path.abspath(caller_file))
        else:
            script_dir = os.getcwd()
        
        config_path = os.path.join(script_dir, 'config.ini')
        if os.path.isfile(config_path):
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            try:
                return config.getboolean('SCAN', 'scan_original_file', fallback=False)
            except Exception:
                return False
        return False  # 默认跳过
    
    # 其他文件：只处理 .txt 和 .xml
    ext = os.path.splitext(file_path)[1].lower()
    return ext in ('.txt', '.xml')

def resolve_symlink(path):
    """解析符号链接，返回真实路径"""
    try:
        return os.path.realpath(path)
    except:
        return path

# ==================== 4. 显示宽度计算（中文对齐） ====================
def get_display_width(text):
    """计算字符串在控制台中的显示宽度（中文算2）"""
    if text is None:
        return 0
    width = 0
    for ch in str(text):
        if '\u4e00' <= ch <= '\u9fff':
            width += 2
        else:
            width += 1
    return width

def pad_text(text, width):
    """将文本填充到指定宽度，考虑中英文字符宽度差异"""
    if text is None:
        text = ""
    text = str(text)
    cur = get_display_width(text)
    if cur >= width:
        return text
    return text + ' ' * (width - cur)

# ==================== 5. XML/文本解析 ====================
def clean_xml_tags(text):
    """清理XML/HTML标签，如颜色标签"""
    if not text:
        return text
    text = re.sub(r'<color=[^>]*>', '', text)
    text = re.sub(r'</color>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def parse_name_from_xmls(name_id, localization_directory, debug=False):
    """从本地化目录的.xml文件中解析name_id对应的文本"""
    if not localization_directory or not os.path.exists(localization_directory):
        if debug:
            print(f"调试: 本地化目录不存在: {localization_directory}")
        return None

    # 收集本地化目录下所有.xml文件
    xml_files = []
    for file in os.listdir(localization_directory):
        if file.lower().endswith('.xml'):
            xml_files.append(os.path.join(localization_directory, file))

    if not xml_files:
        return None

    # 遍历所有XML文件查找匹配项
    for xml_file in xml_files:
        try:
            # 方法1: 使用ElementTree解析
            import xml.etree.ElementTree as ET
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                for elem in root.iter():
                    elem_id = elem.get('id')
                    if elem_id == name_id:
                        text = elem.text
                        if text:
                            return clean_xml_tags(text)
            except ET.ParseError:
                pass

            # 方法2: 使用正则表达式作为备选
            with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            pattern = rf'<text\s+id\s*=\s*["\']{re.escape(name_id)}["\'][^>]*>(.*?)</text>'
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1).strip()
                return clean_xml_tags(text)
        except Exception:
            continue
    return None

# ==================== 6. 模组文件夹信息 ====================
def get_mod_folder_and_time(file_path, root_path):
    """获取文件所属的模组文件夹和修改时间"""
    try:
        real_file_path = resolve_symlink(file_path)
        real_root_path = resolve_symlink(root_path)
        try:
            rel_path = os.path.relpath(real_file_path, real_root_path)
        except ValueError:
            rel_path = real_file_path
        path_parts = rel_path.split(os.sep)
        if len(path_parts) > 1 and path_parts[0] not in ('..', '.'):
            mod_folder_name = path_parts[0]
            mod_folder_path = os.path.join(real_root_path, mod_folder_name)
            if os.path.exists(mod_folder_path):
                mod_time = os.path.getmtime(mod_folder_path)
                return mod_folder_name, mod_time, mod_folder_path
            else:
                return mod_folder_name, None, None
        else:
            return "Root", os.path.getmtime(real_file_path), real_root_path
    except (ValueError, OSError):
        return "Unknown", None, None

def find_localization_directory(mod_folder_path, preferred_lang='cn'):
    """查找本地化目录，优先cn，然后是en，最后是其他语言"""
    if not mod_folder_path or not os.path.exists(mod_folder_path):
        return None
    language_order = [preferred_lang, 'cn', 'en', 'jp', 'kr']
    for lang in language_order:
        xmls_lang_path = os.path.join(mod_folder_path, "Equipment", "xmls", lang)
        if os.path.exists(xmls_lang_path) and os.path.isdir(xmls_lang_path):
            return xmls_lang_path
    return None

# ==================== 7. 颜色类 ====================
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'

# ==================== 8. 时间格式化 ====================
def format_mod_time(timestamp):
    """将时间戳格式化为 月-日 时:分"""
    if timestamp:
        try:
            return datetime.fromtimestamp(timestamp).strftime('%m-%d %H:%M')
        except:
            pass
    return ""

# ==================== 9. 研发/所属相关（通用版本） ====================
def find_stat_files(mod_folder_path):
    """在模组文件夹中查找Creature/Creatures/*_stat.txt文件"""
    if not mod_folder_path:
        return []
    creature_path = os.path.join(mod_folder_path, "Creature", "Creatures")
    if not os.path.exists(creature_path):
        return []
    stat_files = []
    for root, dirs, files in os.walk(creature_path):
        for f in files:
            if f.lower().endswith('_stat.txt'):
                stat_files.append(os.path.join(root, f))
    return stat_files

def parse_stat_file_for_equipment(stat_file):
    """从_stat.txt文件中提取equipment信息和script信息"""
    equipment = {}
    script_name = None
    try:
        with open(stat_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # 提取script标签
        m = re.search(r'<script>([^<]+)</script>', content, re.IGNORECASE)
        if m:
            script_name = m.group(1).strip()
        # 匹配equipment标签
        pat = r'<equipment\s+[^>]*?\s+equipId\s*=\s*["\']([^"\']*)["\'][^>]*?>'
        for equip_id in re.findall(pat, content, re.IGNORECASE):
            full_pat = rf'<equipment\s+[^>]*?\s+equipId\s*=\s*["\']{re.escape(equip_id)}["\'][^>]*?>'
            match = re.search(full_pat, content, re.IGNORECASE)
            if match:
                tag = match.group(0)
                cost_match = re.search(r'cost\s*=\s*["\']([^"\']*)["\']', tag, re.IGNORECASE)
                cost = cost_match.group(1) if cost_match else "N/A"
                equipment[equip_id.strip()] = {'cost': cost.strip(), 'script_name': script_name}
    except Exception:
        pass
    return equipment

def get_creature_info(script_name, mod_folder_path):
    """获取生物信息（名称）"""
    if not script_name or not mod_folder_path:
        return None
    # 查找CreatureList目录
    creature_list_path = os.path.join(mod_folder_path, "Creature", "CreatureList")
    if not os.path.exists(creature_list_path):
        return None
    # 查找creature ID
    creature_id = None
    for f in os.listdir(creature_list_path):
        if f.lower().endswith('.txt'):
            with open(os.path.join(creature_list_path, f), 'r', encoding='utf-8', errors='ignore') as fp:
                content = fp.read()
            pattern = rf'<creature\s+[^>]*?\s+name\s*=\s*["\']{re.escape(script_name)}["\'][^>]*?>'
            for match in re.findall(pattern, content, re.IGNORECASE):
                id_match = re.search(r'id\s*=\s*["\']([^"\']*)["\']', match)
                if id_match:
                    creature_id = id_match.group(1).strip()
                    break
            if creature_id:
                break
    if not creature_id:
        return None
    # 查找creature名称
    creature_info_path = os.path.join(mod_folder_path, "Creature", "CreatureInfo", "cn")
    if not os.path.exists(creature_info_path):
        return None
    for f in os.listdir(creature_info_path):
        if f.lower().endswith(('.txt', '.xml')):
            with open(os.path.join(creature_info_path, f), 'r', encoding='utf-8', errors='ignore') as fp:
                content = fp.read()
            pattern = rf'<info\s+id\s*=\s*["\']{re.escape(creature_id)}["\'][^>]*?>(.*?)</info>'
            for info_content in re.findall(pattern, content, re.DOTALL | re.IGNORECASE):
                name_pattern = r'<name\s+openLevel\s*=\s*["\'][^"\']*["\'][^>]*?>(.*?)</name>'
                names = re.findall(name_pattern, info_content, re.DOTALL | re.IGNORECASE)
                if names:
                    return names[-1].strip()
    return None

def get_equipment_details(equip_id, mod_folder_path):
    """获取装备详细信息（研发所需cost和所属生物）"""
    if not mod_folder_path:
        return {"cost": "N/A", "belongs_to": "N/A"}
    for stat_file in find_stat_files(mod_folder_path):
        eq_dict = parse_stat_file_for_equipment(stat_file)
        if equip_id in eq_dict:
            info = eq_dict[equip_id]
            cost = info['cost']
            script = info.get('script_name')
            belongs = "N/A"
            if script:
                creature = get_creature_info(script, mod_folder_path)
                if creature:
                    belongs = creature
            return {"cost": cost, "belongs_to": belongs}
    return {"cost": "N/A", "belongs_to": "N/A"}
