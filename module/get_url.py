"""
url打开模块
打开网页, 保存html源码
"""
import gzip
import http.cookiejar
import socket
import traceback
import urllib.error as urlerr
import urllib.request as urlreq
from http.client import HTTPResponse
from urllib.parse import urlencode, urlparse

import requests
import requests.utils as requtils

from module import config
from module.exception import *
from module.log import logger
from module.utils import *

_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
    }
_MAX_ERROR_OPEN = 3
_MAX_ERROR_SAVE = 2


class UrlConfig:
    method = "GET"  # 默认
    headers = {}
    cookies = {}
    cut_rule = None
    time_out = 16
    delay: tuple = (2, 3)
    next_pages: str = ""

    def __init__(self, settings=None) -> None:
        """
        读 settings.json 获得method, delay, headers和cookies
        """
        settings = settings if settings else config.get_task()
        openConfig = settings["OpenConfig"]
        for k, v in openConfig.items():
            if k == "cookies":
                v = cookie_str_to_dict(v)
            setattr(self, k, v)
        if "User-Agent" not in self.headers:
            self.headers["User-Agent"] = _HEADERS

    def params(self):
        return {
            "headers": self.headers,
            "cookies":self.cookies,
            "timeout": self.time_out
        }

    def save_cookies(self):
        config.set_task("OpenConfig.Cookies", self.cookies)
        config.save()


class Response:
    response: str = None

    def __init__(self, rule):
        self.cut = init_re(rule)
        logger.info(f"{config.name}: cut_rule: {rule}")

    def cut_html(self, rule: dict or str = None):
        """ 裁剪得到的html源码, 保存到 self.html_cut
        某些html含过多无用信息,使用bs解析会变得非常慢,
        如zzlh的招标列表页面源码有一万多行的无用信息(目录页码),
        需要删去部分无用信息
        Html对象使用 search方式获得group的值

        Args:
            rule (dict, str): 仅在测试中使用,裁剪的规则
                当 cut_rule 为str 时使用re.S 额外参数: . 匹配换行符 \n
                为dict时如下所示 \n
                cut_rule = {
                    "re_rule": "正则表达式",
                    "rule_option": "re.compile额外参数, 默认为re.S, 
                        re.S无法保存在json中,所以使用re.S在python中的 int值,值为 16"
                }
        Returns:
            html_cut(str): 使用正则裁剪后的html源码,也有可能不裁剪
        """
        logger.info("get_url.cut_html")
        if rule:
            if isinstance(rule, dict):
                html_cut = re.search(rule["re_rule"], self.response,
                                     rule["rule_option"])
            else:
                html_cut = self.response if rule == "" else \
                           re.search(rule, self.response, re.S)
        else:
            html_cut = self.cut.search(self.response)
        if html_cut is None:
            raise CutError
        return html_cut.group()

    def save_response(self, rps="", url="", path="./html_error/",
                      save_date=False, extra=""):
        """
        保存response，仅在浏览列表页面出错时或测试时保存使用

        Args:
            rps (str): response,为空时使用self.url_response_byte
            url (str): 网页url,为空时使用self.req.full_url
            path (str): html文件相对路径,默认为 ./html_error
            save_date (bool): 是带有保存带时间的新文件
            extra:
        Returns:
            file_name (str): 保存的文件名
        """
        if isinstance(url, dict):
            data = url["form"] if "from" in url else ""
            full_url = url["url"]
        else:
            full_url = url
        rps = self.response if not rps else rps
        path = f"{path}/" if path[-1] != "/" else path
        file_name = path + url_to_filename(full_url)
        name_list = file_name.split(".")
        # 添加额外名称
        if isinstance(url, dict) and data:
            name_list[-2] = f"{name_list[-2]}_{urlencode(data)}"
        elif isinstance(url, dict) and data is None:
            name_list[-2] = f"{name_list[-2]}_from={data}"
        if save_date:
            name_list[-2] = f"{name_list[-2]}{date_now_s(True)}"
        if extra:
            name_list[-2] = f"{name_list[-2]}_{extra}"
        file_name = ".".join(name_list)
        save_file(file_name, rps)
        logger.info(f"save html as {file_name}")
        return file_name

    def get_response_from_file(self, file, save="response"):
        """ 将文件读取的数据赋给self.url_response_byte, 仅在测试中使用
        Args:
            file (str): file路径或html字符串
            save (str): url_response_byte: 保存在 self.url_response中
                        html_cut: 保存在 self.html_cut中
        """
        logger.hr("get_url.get_response_from_file", 3)
        try:
            with open(file, "r", encoding="utf-8") as f:
                response = f.read()
            logger.info(f"read html from file: {file.strip()[:100]}...")
        except (FileNotFoundError, OSError):
            response = file
            logger.info(f"read html from str: {file.strip()[:100]}...")
        setattr(self, save, response)


class GetList:
    list_url = ""
    error_open = 0
    r: requests.models.Response = None

    def __init__(self):
        self.config = UrlConfig()
        self.res = Response(self.config.cut_rule)
        self.s: requests.Session = requests.Session()
        self.s.cookies = requtils.cookiejar_from_dict(self.config.cookies)

    def url_extra(self, url, **kwargs):
        return url

    def open(self, url, open_times=0, save_error=0):
        self.res.response = ""
        open_times += 1
        logger.info(f"open {url}\n{open_times} open")
        if open_times > _MAX_ERROR_OPEN:
            raise TooManyErrorOpen
        self.list_url = url
        error = ""
        try:
            self._open()
        except Exception:
            error = f"open error: {self.list_url}\n{traceback.format_exc()}"
        if not error:
            try:
                html_cut = self.res.cut_html()
            except Exception:  # html AttributeError json 
                error = f"cut error: {self.list_url}\n{traceback.format_exc()}"
                if save_error < _MAX_ERROR_SAVE:
                    save_error += 1
                    self.res.save_response(url=self.list_url,
                                        save_date=True, extra="cut_Error")
        if error:
            logger.error(error)
            sleep_random(self.config.delay)
            self.open(url, open_times, save_error)
        return html_cut

    def _open(self):
        method = self.config.method.upper()
        kwargs = self.config.params()
        if method == "GET":
            self.r = self.s.get(url=self.list_url, **kwargs)
        elif method == "POST":
            url, data = self.list_url.values()
            self.r = self.s.post(url=url, data=data, **kwargs)
        else:
            logger.warning(f"error method: {method}")
            # raise
        self.res.response = self.r.text


class GetUrl:
    # config = UrlConfig()
    url_response_open: HTTPResponse = None
    url_response_byte: bytes = None  # 原始bytes数据 read后
    html_cut: str = None
    response: str = None  # read后的数据再decode, 默认为 utf-8解析
    req: urlreq.Request = None
    url: str or dict = None
    cookie = {}

    # def __init__(self, headers=None, method=None):
    #     self.headers = _HEADERS if headers in (None, {}, "") else headers
    #     self.method = "GET" if method in (None, "") else method.upper()
    #     self.init_req()

    def open(self, url, headers=None, method=None):
        """
        
        Args:
            url (str,dict): GET方式输入str, POST方式输入dict,
                dict应包含 form 信息
            **kwargs (dict): headers信息, method方式
        Returns:
            self.response (str): decode后的源码
        """
        if isinstance(url, dict):
            self.init_req(**url, headers=headers, method=method)
        else:
            self.init_req(url, headers=headers, method=method)
        self._open_url()
        return self.decode_response()

    def init_req(self, url="http://127.0.0.1", 
                 headers: dict = None, method=None, form=None):
        """封装请求头,默认模式为GET
        Args:
            url (str,dict): 请求网址
            headers (dict):
            method (str): 请求模式,默认为GET
            form (dict): 要封装的数据
        saves:
            self.req: urlreq封装的请求头
        """
        if not headers:  # 若无输入则用自己的header
            headers = self.headers
        if not method:
            method = self.method
        method = method.upper()
        self.url = url
        if isinstance(url, dict):
            form = url["form"]
            url = url["url"]
        data = bytes(urlencode(form), encoding="utf-8") if form else None
        self.req = urlreq.Request(url=url, method=method, data=data, headers=headers)
        # if headers:
        #     for head, value in headers.items():
        #         self.req.add_header(head, value)

    def _open_url(self, timeout=12):
        """ 打开self.REQ的网页,保存源码(bytes)到self.url_response_byte中
        Args:
            timeout (int, float): 超时时间，默认为12秒
        Returns:
            self.url_response_byte (byte): 原始的网页byte数据
        """
        logger.info(f"open {self.req.full_url}\n"
                    f"method:{self.req.method}, data:{self.req.data}")
        self.url_response_byte = None
        try:
            self.url_response_open = urlreq.urlopen(self.req, timeout=timeout)
        except (urlerr.HTTPError, urlerr.URLError) as url_error:
            logger.error(
                f"open {self.req.full_url} Failed HTTPError: {url_error}\n"
                f"HTTP Status Code: {url_error.code}\n"
                f"req: url: {self.req.full_url}\nheaders: {jsdump(self.req.headers)}\n"
                f"method: {self.req.method}, data:{self.req.data}")         
            assert False, "open url error"
        except socket.timeout:
            assert False, "socket.timeout: time out"
            # exit(1)

        self.url_response_byte = self.url_response_open.read()
        # self.url_response_byte.info().get("Content-Encoding")

        return self.url_response_byte

    def decode_response(self):
        """
        AttributeError: 'HTTPResponse' object has no attribute 'decode'
        可能会有AttributeError: 'NoneType' object has no attribute 'decode'
        """
        # self.url_response_byte (str): 经过urlopen返回的response.read().decode()后的源码
        decoding = "utf-8"
        try:
            self.response = self.url_response_byte.decode(decoding)
        except UnicodeDecodeError:
            decoding = "gbk"
            try:
                self.response = self.url_response_byte.decode(decoding)
            # 尝试用gzip解压缩
            except UnicodeDecodeError:
                self.url_response_byte = gzip.decompress(self.url_response_byte)
                self.decode_response()
        except AttributeError:
            if self.url_response_byte is None:
                # Q: 是否抛出异常
                logger.error("url_response_byte is None")  # 当网站无返回时
            else:
                self.response = self.url_response_byte  # 仅用于读取文件给url_response
        return self.response



if __name__ == "__main__":
    pass
    #  POST
    # url_open = {
    #     "url":"https://httpbin.org/post",
    #     "form": {
    #         "classId": "151",
    #         "key": "-1",
    #         "page": "1"
    #     }
    # }
    # test_headers = {
    #     "User-Agent": "233",
    #     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    # }
    # url_obj = UrlReq(method="POST")
    # url_obj.init_req(url_open, headers=test_headers)
    # url_obj._open_url()
    # print(url_obj.decode_response())
    # url_obj.save_response(save_date=True, path="./html_test/", extra="test")
    
    # GET
    # url_open = "https://httpbin.org/cookies"
    # test_headers = {
    #     "User-Agent": "233",
    #     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    #     "Referer": "http://www.weain.mil.cn/",
    #     "Accept": "application/json, text/javascript, */*; q=0.01",
    #     "Accept-Encoding": "gzip, deflate",
    #     "Content-Type": "application/json",
    #     "isEncrypt": "isNotEncrypt",
    #     "X-Requested-With": "XMLHttpRequest",
    #     "Cookie": "3333=5454; qsd0=1233"
    # }
    # url_obj = GetUrl()
    # url_obj.open(url_open, headers=test_headers, method="GET")
    # print(url_obj.decode_response())
    # # url_obj.save_response(save_date=True, path="./html_test/", extra="test")
    config.name = "hkgy"
    get_list = GetList()
    get_list.res.get_response_from_file(f"html_error/ebid.eavic.com cms channel ywgg1 index.htm pageNo=1_2023_05_15-17_38_46_cut_Error.html")
    print(get_list.res.cut_html())
