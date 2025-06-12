
def RequestException(res,platform_info_inst,e):
    # 不可用状态的最大巡检次数
    retry_num = platform_info_inst.retry_num + 1
    max_retry_num = platform_info_inst.max_retry_num
    response_code = 500
    if retry_num > max_retry_num:
        enabled = 0
    else:
        enabled = 1

    if res != None and res.text != None:
        response_message = res.text
    else:
        response_message = str(e)
    return enabled,response_code,response_message,retry_num

def RequestNot200(res,platform_info_inst):
    # 不可用状态的最大巡检次数
    retry_num = platform_info_inst.retry_num + 1
    max_retry_num = platform_info_inst.max_retry_num
    response_code = 500
    if retry_num > max_retry_num:
        enabled = 0
    else:
        enabled = 1

    if res != None and res.text != None:
        response_message = res.text
    else:
        response_message = "未知原因"
    return enabled, response_code, response_message,retry_num