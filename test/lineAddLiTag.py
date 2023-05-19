import sys
from json import loads
from os.path import exists

from module import CONFIG
from module.utils import date_days, date_now_s

DATAPATH = "./data"
MATCH = "bid_match"
LIST = "bid_list"
STBFUN = "scrollToBottom()"  # write_function 中的js函数名

TITLE = -4
DATE = -3
URL = -2
TYPE = -1

# "jdcg", "zzlh", "hkgy", "zhzb", "qjc", "cebpub"
WEB = ["jdcg", "zzlh", "hkgy", "zhzb", "qjc", "cebpub"]

date_time = ""

with open(CONFIG, "r", encoding="utf-8") as f:
    config =  loads(f.read())
    TRANSFILE = config["transFile"]

if not TRANSFILE:
    print(f"please check {CONFIG}")
    exit()
for tf in TRANSFILE:
    if tf not in ["list", "match", "dayFile"]:
        print(f"please check {CONFIG}")
        exit()


def write_head(html, name: str, fileType):
    # html <head>标签, 显示标题
    html.write(f"""<head>
    <title>{name}_{fileType}{date_time}</title>
</head>\n""")


def write_body(html, body):
    if body == "top":
        html.write(f"<body onload={STBFUN}>\n")
    elif body == "bottom":
        for _ in range(0,3):
            html.write("<li></li>\n")
        html.write("</body>")


def write_function(html):
    # 页面渲染完成后自动滚到底部
    html.write("""
    <script>
        // 页面渲染完成后自动滚到底部
        function scrollToBottom()
        {
            window.scrollTo(0, document.getElementsByTagName("body")[0].scrollHeight);
        }
    </script>
    """)


def labels_a(title, url):
    return f"<a href=\"{url}\">{title}</a>"


def wirte_li(html, line: str, idx, fileType: str):
    
    line_list = line.rstrip().split("; ")
    labelsA = labels_a(line_list[TITLE], line_list[URL])
    fileType = fileType.lower()
    # TODO 有没有更好的写法
    if fileType == "match":  # match 一行会分为5个 [匹配关键词]; 标题; 日期; url; 类型
        html.write(f"<li>{str(idx)}. {line_list[0]}: {labelsA},"
                   f"{line_list[DATE]},{line_list[TYPE]}</li>\n")
    else:
        html.write(f"<li>{str(idx)}. {labelsA},"
                   f"{line_list[DATE]},{line_list[TYPE]}</li>\n")

def write_html(webName, fileType, txt:str):
    """
    Args:
        webName(str): qjc or dayFile
        fileType(str): match or list
        txt(str): txt file
    """
    
    webFIle = get_file_name(fileType, webName, 'htm', txt)
    with open(webFIle, "w", encoding="utf-8") as html,\
         open(txt, "r", encoding="utf-8") as txtFile:
        write_head(html, webName, fileType)
        write_body(html, "top")
        write_function(html)
        # TODO 有没有更好的写法
        idx = 1
        for line in txtFile:
            if not ";" in line:  # 忽略掉干扰信息
                html.write(f"<li> {line.strip()} <li>\n")
                continue
            wirte_li(html, line, idx, fileType)
            idx += 1
        write_body(html, "bottom")


def get_file_name(fileType, webName, Type="htm", txt=""):
    """
    Argv:
        fileType(str): match or list
        webName(str): qjc or zzlh or dayFile
        Type(str): htm or txt, input html = htm
    """
    global date_time
    if webName == "dayFile":
        date_time = txt[-14: -4] if txt else date_days(format='day')
        return f"{DATAPATH}/bid_day{fileType.title()}_{date_time}.htm"
    elif Type == "txt":
        return f"{DATAPATH}/bid_{fileType}_{webName}.txt"
    elif Type in ["htm", "html"]:
        date_time = date_days(format='day')
        return f"{DATAPATH}/bid_{fileType}_{webName}_{date_time}.htm"


def main():
    # TODO 有没有更好的写法    
    for fileType in TRANSFILE:
        if fileType == "dayFile":
            dayFile()
            break
        for webName in WEB:
            fileName = get_file_name(fileType, webName, "txt")
            if not exists(fileName):
                print(f"{fileName} is not exists")
                return
            write_html(webName, fileType, fileName)


def dayFile():
    today = date_days(format="day")
    for fileType in ["list", "match"]:
        fileName = f"{DATAPATH}/bid_day{fileType.title()}_{today}.txt"
        write_html("dayFile", fileType, fileName)


# 三种情况
# 1. 绝对路径
# 1.1 带参数
# 1.2 不带参数
# 2. 部分文件名,如日期,日期格式为 mm-dd, 年份默认为今年
# TODO 把上面的写完
def command(argv):
    if len(argv) == 1:
        for Type in ["List", "Match"]:
            file = f"{DATAPATH}/bid_day{Type}_{date_days()[:4]}-{argv[0]}.txt"
            write_html("dayFile", Type, file)
    else:
        pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        argv = sys.argv[1:]
        command(argv)
    else:    
        main()
