"""
 本模块的功能为
 对于一个招标网站的 招标项目列表 的 页面 有如下操作
 1. 解析页面, 裁剪页面
 2. 用bs4解析html源码
 3. 解析招标项目所在的tag
 4. 获得招标信息

"""
from bs4 import BeautifulSoup as btfs
from bs4 import Tag

from module.config import config
from module.log import logger
from module.utils import *


# 仅对li_tag中的元素(可能为Tag或dict)进行处理
class BidTag:
    infoList: list = None
    type_r: tuple
    url_r: tuple
    date_r: tuple
    name_r: tuple
    tag: Tag
    rule_now: tuple = None

    def __init__(self, settings=None):
        # settings: 整个task 的settings
        logger.hr("BidTag.__init__", 3)
        settings = settings if settings else config.get_task()
        rule: dict = settings["BidTag"]
        for li_r, value in rule.items():
            self._init_list_rule(li_r, value)

    # TODO 解析规则这部分有点*,记得重写一下
    def _init_list_rule(self, li_r, rule: str):
        """ 将rule以 | 和 : 分隔, 最终得到一个元组,详细说明参考web_brows_test.py
            解析rule, 设置属性值
        Args:
            li_r (str): rule.bid_tag的key, 一般为name_r, date_r, url_r等
            rule (str): rule.bid_tag key对应的value, 
        """
        # 预处理分割rule
        tag_find = tag_name = find_all_idx = value_name = value = None
        if rule is None or rule == "":
            return setattr(self, li_r, (None,))
        if rule.count("|") == 2:  # 2个|认为有 find_all_idx, 用于find_all的索引
            tag_gets_r, value_gets_r, find_all_idx = rule.split("|")
        elif rule.count("|") == 1:  # 必须有1个 |
            tag_gets_r, value_gets_r = rule.split("|")
        elif rule.count("|") == 0:
            return setattr(self, li_r, (rule,))
        if tag_gets_r:
            tag_find, tag_name = tag_gets_r.split(":")
        if value_gets_r:
            value_name, value = value_gets_r.split(":")
        setattr(
            self, li_r, (tag_find, tag_name, find_all_idx, value_name, value))

    def get(self, bid_tag: Tag or dict) -> list:
        """ 用规则获得一个tag或dict中对应的数据
         return [name, date, url, b_type]
        Args:
            bid_tag (Tag or dict): 招标项目对象
        """
        self.tag = bid_tag
        self.infoList = []
        self.infoList.append(self.parse_rule(bid_tag, *getattr(self, "name_r")))
        self.infoList.append(self.parse_rule(bid_tag, *getattr(self, "date_r")))
        self.infoList.append(self.parse_rule(bid_tag, *getattr(self, "url_r")))
        self.infoList.append(self.parse_rule(bid_tag, *getattr(self, "type_r")))
        # for key in ("name_r", "date_r", "url_r", "type_r"):
        return self.infoList

    # TODO 写的太*了，记得重写,包括下面的_parse_bs_rule
    def parse_rule(self, tag: Tag or dict, *args) -> Tag or None or str:
        """ 判断tag类型, 接收规则并解析
        
        """
        self.rule_now = args
        if isinstance(tag, Tag):
            return _parse_bs_rule(tag, *args)

        elif isinstance(tag, dict) or isinstance(tag, list):
            return _parse_json_rule(tag, *args)
        return None


def _parse_bs_rule(tag: Tag,
                   tag_find="", tag_name="", find_all_idx=None,
                   value_name="", value="", bb ="") -> None or str:
    """
    解析规则,找到tag或tagList(bs4.element.ResultSet),或符合规则的属性值或tag中的文本
    Args:
        tag (bs4.element.Tag): 要检索的tag
    Returns:
        tag or text or None, 可能有三种返回
        None: not rule 为 True时返回None
        tag (bs4.element.Tag, bs4.element.ResultSet): find或find_all的检索结果
        text (str): tag的内容文本, 或tag中符合规则的属性的值
    """
    if not tag_find:  # 无rule返回None
        return None
    # 检索tag
    if tag_find == "tagName_all":
        if value_name and value:  # 若有value检索要求,则find_all加上参数attrs
            tag = tag.find_all(tag_name, attrs={value_name: value})
        # 无value要求,直接用find_all搜索
        # 使用find_all(tag_name, attrs={"":""}) 会返回None,所以这里额外调用语句
        else:
            tag = tag.find_all(tag_name)
        if find_all_idx:  # 若有find_all 的索引要求,则返回该索引对应的tag
            if find_all_idx != "all":
                tag = tag[int(find_all_idx)]
    elif tag_find == "tagName_find":  # 使用tagName,find方式检索
        if tag_name:
            tag = bs_deep_get(tag, tag_name)  # 调用额外函数返回Tag
    # 检索属性值
    if value_name:  # value_name有值 则检索属性值
        if value_name == "class":
            if "".join(tag.get("class")) == value.replace(" ", ""):
                return tag.text.strip()  # class=value 的 text值
            else:  # 若当前tag的class不符合则用find
                return tag.find(class_=value).text.strip()  # tag内容文本
        elif value_name == "_Text":  # 没有属性只有text的标签
            if find_all_idx == "all":
                return f"{tag[0].text.strip()}|{tag[1].text.strip()}"
            return tag.text.strip()  # tag内容文本
        else:
            return tag.get(value_name).strip()  # tag属性值
    else:  # 若不检索属性值则直接返回tag
        return tag


def _parse_json_rule(tag: list or dict,
                     key_find=None, list_idx=None, *kwargs):
    """ 根据规则获得dict 或 list中的值

    Args:
        tag (dict or list):
    Returns:
        str or None
    """
    if isinstance(tag, dict):
        return deep_get(tag, list_idx)
    elif isinstance(tag, list):
        return tag[list_idx]


class BidBase:
    # 解析后的bid信息
    # BidBase: 用于 module.web 中的继承，保存一个网页列表中招标项目的最终信息
    type: str
    url: str
    date: str
    name: str
    name_cut: re.Pattern = None
    date_cut: re.Pattern = None
    type_cut: re.Pattern = None
    url_cut: re.Pattern = None
    url_root: str
    infoList: list = None
    rule_now: str

    def __init__(self, settings=None):
        """ 定义项目对象,

        Args:
            settings (dict): 需要一整个task的设置
        """
        logger.hr("Bid.__init__", 3)
        settings = settings if settings else config.get_task()
        rule = settings["BidBase"]["re"]
        for k, v in rule.items():
            setattr(self, k, init_re(v))
            logger.debug(f"rule init {k}: {getattr(self, k)}")
        self.url_root = settings["BidBase"]["urlRoot"]

    def receive(self, *args):
        """ 接收BidTag.get()返回的list
        Args:
            *args: (name, date, url, type)
        """
        for idx, key in enumerate(("name", "date", "url", "type")):
            self.rule_now = key
            rule = getattr(self, f"{key}_cut")
            setattr(self, key, _re_get_str(args[idx], rule))

        self._url()  # TODO 是否应该根据type进行选择?
        self._date()
        self._name()
        self._date()
        self.infoList = [self.name, self.date, self.url, self.type]

    def _url(self):
        """ 用 前缀加上后缀得到网址
        输入bid_root对 json中的 name.url_open.url_root 进行查表
        Args:
            bid_root (str): 前缀索引
            bid_tail (str): 后缀
        """
        # if self.type in self.url_root:
        #     self.url = f"{self.url_root[self.type]}{self.url}"
        # else:
        self.url = f"{self.url_root}{self.url}"

    def _name(self):
        pass

    def _type(self):
        if self.type in ["", " ", None]:
            self.type == "None"

    def _date(self):
        self.date = self.date.replace("年", "-").replace("月", "-").replace("日", "")

    def message(self) -> str:
        # infoList 的最后一位可能是 None
        return f"{'; '.join(self.infoList[:-1])}; {str(self.infoList[-1])}"


def _re_get_str(obj: str, rule: re.Pattern = None, cut_rule=None):
    """ 正则获取字符串

    Args:
        obj: 被匹配的字符
        rule: 编译好的正则
        cut_rule: 正则表达式, 仅在测试中使用
    Returns:
        (str): 返回re.search搜索结果
    """
    # 默认正则参数 (4)(数字)+(_,-,年)+(2)(数字)+(_,-,月)+(2)(数字)+(日),日可忽略
    if isinstance(cut_rule, str):
        return re.search(cut_rule, obj).group()
    if rule is None or rule.pattern == "":
        return obj
    return rule.search(obj).group()


class ListBrows:
    """
    项目列表页面对象
    """
    html_cut = ""  # cut_html 后保存
    bs: Tag or dict = None

    def __init__(self, settings=None):
        settings = settings if settings else config.get_task()
        self.tag_list: str = settings["brows"]["tag_list"]

    def get_tag_list(self, page=None, tag_list=None, parse="html.parser", t=""):
        """
        输入 str 调用 bs生成self.bs 从self.bs 里根据tag_list提取list
        Args:
            tag_list:
            page:(str) html源码,解析获得self.bs,或从 self.url_response 或
            parse (str): 解析html的bs4模式 默认为 html.parser
            t ()
        Returns:
            bid_list (list): 提取到的list
        """
        logger.info("web_brows.Html.get_tag_list")
        if not tag_list:  # 仅测试中使用
            tag_list = self.tag_list
        if isinstance(page, str):
            self.html_cut = page
            logger.info(f"get tag list from \"{page.strip()[: 100]}\"")

        self.bs = btfs(self.html_cut, features=parse)  # bs解析结果
        return self.bs.find_all(tag_list)


# class BidHtml(ReqOpen):
#     def __init__(self, settings):
#         pass


if __name__ == "__main__":
    # 这里只是测试对象的单个功能,要测试对一个页面的功能需要用 ./test/web_brows_test.py
    json_file = "./bid_settings/bid_settings.json"
    json_settings = read_json(json_file)
    # html_file = r""
    # url = ""
    task = "zgzf"
    # zgzf = web_brows_init(json_settings, task)
    # zgzf.open("http://127.0.0.1:19999/get")
    # zgzf.get_response_from_file(html_file)
    # zgzf.set_cookie()
    pass
