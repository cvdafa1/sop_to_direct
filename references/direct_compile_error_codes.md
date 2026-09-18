# 编译相关错误码（error.compile.*）

| 10进制错误码 | 错误码常量 | 中文 | English |
| --- | --- | --- | --- |
| -268268987 | ERROR_COMPILE_REQUEST_REQ_REPLY_BIND_VALUE_CONSTANT | 响应绑定值[{0}]不允许为固定值 | Request reply bind value [{0}] not allow fixed value |
| -267508795 | ERROR_COMPILE_VAR_INVALID_ENUM_SET | 变量[{0}]关联的枚举集[{1}]不存在 | The enumeration set [{1}] associated with variable [{0}] does not exist |
| -267270923 | ERROR_COMPILE_INVALID_ALIAS_TYPE | [{0}]无效的别名 | [{0}]Invalid alias |
| -266210451 | ERROR_COMPILE_ALIAS_NAME_ILLEGAL | [{0}]别名名称由不超过{1}个字符的字母、数字、下划线组成，格式为@(别名)并且首字母必须为字母 | [{0}]Alias name is consisted of up to {1} character letter, number, underscore in the format @ (alias) and starts with letter |
| -266024327 | ERROR_COMPILE_PARAM_NO_BOUND_ENUM_SET | 参数[{0}]未关联枚举集 | Parameter[{0}] is not bound with an enumeration set |
| -260966457 | ERROR_COMPILE_CONSTANT_INT_ILLEGAL | [{0}]整型常量最多允许{1}位 | [{0}]Integer constants can be up to {1} digit |
| -260827213 | ERROR_COMPILE_DEVICE_TEMPLATE_ENUM_PARAM_INVALID | 设备模板步选择的枚举参数[{0}]没有匹配的设备选择步 | Device template step enum param [{0}] invalid |
| -257843293 | ERROR_COMPILE_TREND_ALIAS_NOT_EXIST | 别名[{0}]在子程序[{1}]中不存在 | Alias [{0}] not exist in Subprocedure [{1}] |
| -257350035 | ERROR_COMPILE_FM_REPEATED_PROC_CMD | 重复的程序命令操作 | Repeated procedure command operation |
| -256836116 | ERROR_COMPILE_MISMATCH_ALIAS_DATATYPE | 别名[{0}]数据类型与内容[{1}]数据类型不匹配 | Unmatched data type between alias[{0}] and its content[{1}] |
| -252778852 | ERROR_COMPILE_SELF_CHECK | [{0}]不可自我校验 | [{0}]Cannot check value with itself |
| -249929742 | ERROR_COMPILE_OUTPUT_PARAM_ONLY | [{0}]仅支持使用输出参数 | [{0}]Only output parameter is supported |
| -248142535 | ERROR_COMPILE_FAILED_TO_READ_XLSX_FILE | xlsx文件读取失败 | Failed To Read xlsx File |
| -247818342 | ERROR_COMPILE_EMPTY_WAIT_DATA | 等待时间为空 | No wait time found |
| -246449900 | ERROR_COMPILE_PARAM_BIND_MULTI_DEVICE_ENUM_SET | 参数[{0}]关联的枚举集[{1}]被多个设备绑定 | The enumeration set [{1}] associated with param [{0}] is bound to multiple devices |
| -245814222 | ERROR_COMPILE_FM_LOCAL_PARAM_NOT_ALLOWED | FailMonitor不能使用局部参数/变量[{0}] | Local parameters or variables[{0}] are not allowed in FailMonitor |
| -245531863 | ERROR_COMPILE_FAILED_TO_WRITE_CSV_FILE | csv写入文件失败 | Failed To Write csv File |
| -243342619 | ERROR_COMPILE_MAX_INPUT_LIMIT | 输入不允许超过{0}路 | Up to {0} channel of input |
| -243009112 | ERROR_COMPILE_EMPTY_PROPERTY | 未对步作任何配置 | Step has no configuration |
| -241529703 | ERROR_COMPILE_INVALID_DATATYPE_TAG | [{0}]位号必须是整型/开关量 | [{0}]Tag must be int/bool |
| -241478733 | ERROR_COMPILE_FILE_TOO_LARGE | 文件大小超过限制 | The File Is Too Large |
| -239462475 | ERROR_COMPILE_UNSPECIFIED_DATATYPE_TAG | [{0}]未知数据类型的位号 | [{0}]Unspecified datatype tag |
| -238354038 | ERROR_COMPILE_EMPTY_DESCRIPTION_CHARS | 描述不可为空 | Empty description |
| -229824590 | ERROR_COMPILE_UPPER_LOWER_LIMIT | [{0}]上限值必须不小于下限值 | [{0}]The upper limit must be not less than the lower limit |
| -229723163 | ERROR_COMPILE_EXCEL_ROW_NUMBER_INVALID | 行 [{0}] 必须为整型 | Invalid Csv Row Number: [{0}] |
| -224869490 | ERROR_COMPILE_SCAN_CODE_VARIABLE_ILLEGAL | 扫码编码规则内的占用变量不能以下划线开头[{0}] | Underline cannot be used at the first place of a placeholder variable[{0}] which is in the scan code rule |
| -224058685 | ERROR_COMPILE_DUPLICATE_TAG | 位号和别名同时重复 | Duplicate tag and alias |
| -221994549 | ERROR_COMPILE_EMPTY_CHECKING_TAG | [{0}]未选择校验位号 | [{0}]Empty checking tag |
| -219754247 | ERROR_COMPILE_TAG_NAME_ILLEGAL | [{0}]位号名称由不超过{1}个字符的字母、数字、下划线、横杠、斜杠、反斜杠、小数点组成，格式为#(位号名称)并且首字母必须为字母或数字 | [{0}]Tag name is consisted of up to {1} character letter, number, underscore, hypens, forward slashes, back slashes and decimal point, in the format #(tag name) and starts with letter or number |
| -219447726 | ERROR_COMPILE_VAR_NAME_ILLEGAL | [{0}]变量名称由不超过{1}个字符的字母、数字、下划线组成，格式为$(变量名称)或$$(变量名称)并且首字母必须为字母 | [{0}]Variable name is consisted of up to {1} character letter, number, underscore in the format $ (variable name) or $$ (variable name) and starts with letter |
| -216790910 | ERROR_COMPILE_EMPTY_TIMER | 选择一个计时器 | Please select a timer |
| -216717476 | ERROR_COMPILE_DELAY_TIME_OUT_OF_RANGE | 保持时间范围应为0 ~ {0} | The Time for maintaining should be between 0 and {0} |
| -214671486 | ERROR_COMPILE_DOUBLE_PARAM_ONLY | [{0}]仅支持使用浮点参数 | [{0}]Only double parameter is supported |
| -213854666 | ERROR_COMPILE_ONE_START | 程序有且只能有1个起始步 | Each procedure have and only have one single Start Step |
| -212868200 | ERROR_COMPILE_PARAM_VAR_CONSTANT_ONLY | [{0}]仅支持使用参数/变量/常量 | [{0}]Only parameter/variable/constants is supported |
| -212835886 | ERROR_COMPILE_NUMBERIC_PARAM | [{0}]参数必须为数值类型 | [{0}]Parameter must be of numberic type |
| -212692174 | ERROR_COMPILE_TIMER_NAME_ILLEGAL | [{0}]计时器名称由不超过{1}个字符的字母、数字、下划线组成，格式为$(计时器)并且首字母必须为字母 | [{0}]Timer name is consisted of up to {1} character letter, number, underscore in the format $ (timer) and starts with letter |
| -212042083 | ERROR_COMPILE_FM_INVALID_FORMULA_GROUP | 主程序属性绑定公式组无效 | Invalid formula group |
| -211321189 | ERROR_COMPILE_JUDGE_TYPE_ILLEGAL | [{0}]左侧数据类型为字符串时只能使用"=="与"!="作为判断条件 | [{0}]You can only use "==" or "!=" as a judgement condition when the data type is of string parameter/variable shown on the left side |
| -210016328 | ERROR_COMPILE_EMPTY_SUBPROC_ID | 目标子程序不可为空 | Empty subprocedure isn't allowed |
| -209757264 | ERROR_COMPILE_ALGORITHM_IN_EDIT | 算法模块[{0}]未生效 | Algorithm module [{0}] is not effective |
| -208993724 | ERROR_COMPILE_EMPTY_MESSAGE | 消息为空 | Message is empty |
| -208189529 | ERROR_COMPILE_EMPTY_RUNNING_SEQUENCE | 程序运行流程不能为空 | Empty procedure running sequence isn't allowed |
| -206621961 | ERROR_COMPILE_NUMBERIC_ALIAS | [{0}]别名必须为数值类型 | [{0}]Alias must be of numberic type |
| -204550212 | ERROR_COMPILE_MIN_ONE_INPUT | 至少1路输入 | At least one channel of input is required |
| -204447099 | ERROR_COMPILE_EMPTY_DATA | 未配置任何数据 | No data configuration |
| -204418824 | ERROR_COMPILE_EMPTY_PACKAGES | 未选择投料包号参数 | Empty packages parameter |
| -204028238 | ERROR_COMPILE_EMPTY_CALC_EXPRESSES | 未添加数值计算表达式 | No calculation expression added |
| -203874954 | ERROR_COMPILE_JUDGE_TYPE_INVALID | 无效的判断条件 | Invalid judgment type |
| -203358879 | ERROR_COMPILE_SCAN_CODE_EMPTY_RULE | 未添加扫码编码规则 | Scan code rules not set |
| -202931315 | ERROR_COMPILE_EMPTY_PIN_NAME | 引脚名不能为空 | Pin name can not be empty |
| -196493616 | ERROR_COMPILE_DATA_TYPE_MISMATCH | [{0}][{1}]数据类型不匹配 | [{0}][{1}]Data type not match |
| -195284668 | ERROR_COMPILE_XLSX_SHEET_NAME_EMPTY | sheet名称为空 | Sheet Name is Empty |
| -195123908 | ERROR_COMPILE_EMPTY_ALIAS_CONTENT | [{0}]别名内容为空 | [{0}]Empty alias content |
| -192544703 | ERROR_COMPILE_SCAN_CODE_PLACEHOLDER_REPEATED | 重复的占位变量：{0} | Repeated placeholder variable: {0} |
| -192235230 | ERROR_COMPILE_PARAM_NAME_ILLEGAL | [{0}]参数名称由不超过{1}个字符的字母、数字、下划线组成，格式为$(参数名称)或$$(参数名称)并且首字母必须为字母 | [{0}]Parameter name is consisted of up to {1} character letter, number, underscore in the format $ (parameter name) or $$ (parameter name) and starts with letter |
| -191793060 | ERROR_COMPILE_SUBPROC_NOT_EXIST | 子程序不存在 | Subprocedure isn't existed |
| -191751517 | ERROR_COMPILE_ENUM_LESS_THAN_LOWER_LIMIT | 枚举[{0}]小于写值下限 | Enumeration[{0}] is less than lower limit |
| -190528819 | ERROR_COMPILE_SCAN_CODE_PLACEHOLDER_NOT_EXIST | 不存在的占位变量：{0} | Non-existent placeholder variable: {0} |
| -190444754 | ERROR_COMPILE_EMPTY_SUBPROC_NAME | 子程序名称不能为空 | Subprocedure name must not be empty |
| -190130525 | ERROR_COMPILE_BRANCH_UNIMPLEMENTED | 有输出未选择对应的分支 | Each output must select a corresponding branch |
| -188836813 | ERROR_COMPILE_NUMBERIC_TAG | [{0}]位号必须为数值类型 | [{0}]Tag must be of numerical type |
| -188527019 | ERROR_COMPILE_TREND_TYPE_NEED_NUM | 趋势位号[{0}]类型必须为数字 | Tag [{0}] must be numeric |
| -188494599 | ERROR_COMPILE_CONSTANT_STR_ILLEGAL | [{0}]字符常量不超过{1}个字符（不包括引号） | [{0}]Character constants can be up to {1} single byte excluding quotation marks |
| -185764399 | ERROR_COMPILE_REQUEST_EMPTY_METHOD | 请求的方法不允许为空 | Empty method |
| -185502427 | ERROR_COMPILE_PARAM_DEFAULT_VALUE_TYPE | 参数[{0}]默认值类型错误 | Parameter[{0}] default value type error |
| -184373523 | ERROR_COMPILE_FORBIDDEN_START_IN_PARALLEL | 起始步不能出现在并行步中 | Start Step is not allowed to be added into a Parallel Step |
| -184306862 | ERROR_COMPILE_EMPTY_CHECKING_VALUE | [{0}]空的校验值 | [{0}]Empty checking value |
| -180052257 | ERROR_COMPILE_NONEXISTENT_PARAM_VAR | [{0}]不存在的参数/变量 | [{0}]Nonexisting parameter/variable |
| -179632631 | ERROR_COMPILE_QUEUE_NOT_EXIST | 运行设备不存在 | The run device does not exist |
| -177887966 | ERROR_COMPILE_INVALID_CHECKED_TAG | [{0}]被校验的位号不在数据列表中 | [{0}]Invalid checked tag |
| -177579434 | ERROR_COMPILE_INVALID_BOX_INPUT | [{0}]无效的输入数据 | [{0}]Invalid input |
| -176615803 | ERROR_COMPILE_ENUMS_EMPTY | 枚举集[{0}]内没有枚举 | Enumeration set[{0}] contains no enumeration |
| -176496733 | ERROR_COMPILE_NO_FILE_IN_PATH | 文件路径中未找到对应文件 | No File in Path |
| -175003120 | ERROR_COMPILE_VAR_ENUM_BIND_MULTI_RUN_QUEUE | 变量[{0}]关联的枚举集[{1}]的枚举[{2}]被多个设备关联 | The enumeration [{2}] in enum set [{1}] associated with variable [{0}] is linked to multiple device |
| -173623879 | ERROR_COMPILE_MAX_TWO_OUTPUT | 输出不允许超过2路 | Up to 2 channels of output |
| -172107283 | ERROR_COMPILE_USE_TIMER_AS_VAR | [{0}]无法将计时器作为参数/变量使用 | [{0}]Cannot use timer as parameter or variable |
| -172106195 | ERROR_COMPILE_CHECK_TAG_MULTI_TIMES | [{0}]在一个步中只能对同一个位号校验一次 | [{0}]You can only check the same tag once in a single step |
| -170079177 | ERROR_COMPILE_NO_BRANCH_CONFIGURED | 未配置任何分支 | No branch is configured |
| -167667447 | ERROR_COMPILE_VAR_NO_BOUND_ENUM_SET | 变量[{0}]未关联枚举集 | Variable[{0}] is not bound with an enumeration set |
| -167238399 | ERROR_COMPILE_NO_SPECIFIC_STEP | 程序至少包含一个除了起始、结束、组、文本框之外的步 | Each procedure must contain at least 1 another step except for the Start/End/Group/Text step |
| -167066077 | ERROR_COMPILE_EMPTY_LEFT_VALUE | 在左侧输入框中选择一个位号/参数/变量 | Please select a tag or parameter or variable in the box on the left side |
| -164874698 | ERROR_COMPILE_STRING_PARAM_ONLY | [{0}]仅支持使用字符串参数 | [{0}]Only string parameter is supported |
| -164661465 | ERROR_COMPILE_MAX_CONCAT_CHARS | [{0}]每个输入框中的字符长度不能超过{1} | [{0}]No more than {1} characters is allowed in each box |
| -164519067 | ERROR_COMPILE_REPEATED_OUTPUT | 重复的输出 | Repeated output |
| -164381375 | ERROR_COMPILE_FM_NO_OPERATION | 未设置操作 | Empty operation |
| -163340408 | ERROR_COMPILE_FAILED_TO_READ_CSV_FILE | csv文件读取失败 | Failed To Read csv File |
| -162094113 | ERROR_COMPILE_EMPTY_ALIAS_STRUCT_NAME | [{0}]别名结构体名称为空 | [{0}]Empty alias struct name |
| -161829759 | ERROR_COMPILE_PARALLEL_UNSPECIFIED_END_COND | 未指定并行步任务结束条件 | Unspecified parallel step task end condition |
| -161352235 | ERROR_COMPILE_BRANCH_NEED_UPDATE | 分支{0}需要更新 | Branch{0} needs updating |
| -160906308 | ERROR_COMPILE_SCAN_CODE_RULE_ILLEGAL | 无法识别扫码编码规则 | Unable to recognize scan code rule |
| -157824491 | ERROR_COMPILE_DUPLICATE_BRANCH | [{0}]和[{1}]配置了重复的设备 | [{0}] and [{1}] have duplicated device |
| -152535758 | ERROR_COMPILE_MAX_OUTPUT_LIMIT_BRANCH | 不允许超过{0}路输出 | Up to {0} channel of output |
| -152113313 | ERROR_COMPILE_DEVICE_EMPTY_DEVICE | 设备未配置 | Device not configured |
| -151370114 | ERROR_COMPILE_EMPTY_RIGHT_VALUE | 在右侧输入框中选择一个位号/参数/变量，或输入一个值 | Please select a tag or parameter or variable or enter a value in the box on the right side |
| -151338719 | ERROR_COMPILE_REQUEST_EMPTY_URL | 请求的Url不允许为空 | Empty url |
| -149689194 | ERROR_COMPILE_BRANCH_NOT_CONNECTED | 分支{0}未连接 | Branch{0} is not connected |
| -140739393 | ERROR_COMPILE_INVALID_CLOCK_TYPE | 时钟类型无效 | Invalid clock type |
| -140176043 | ERROR_COMPILE_PARAM_INVALID_ENUM_SET | 参数[{0}]关联的枚举集[{1}]不存在 | The enumeration set [{1}] associated with parameter [{0}] does not exist |
| -140003171 | ERROR_COMPILE_INVALID_ACKNOWLEDGE_TYPE | 无效的确认类型 | Invalid ACK type |
| -139650426 | ERROR_COMPILE_EMPTY_REF_MAIN_PROC_NAME | 引用主程序名称不能为空 | Empty reference main procedure name isn't allowed |
| -136604161 | ERROR_COMPILE_ALGORITHM_OVERDUE | 算法模块[{0}]已废弃 | Algorithm module [{0}] is abandoned |
| -136130899 | ERROR_COMPILE_TEMPLET_IN_TEMPLET | 模板不能包含模板 | Template is not allowed inside another template |
| -134963081 | ERROR_COMPILE_INVALID_PROC | 程序至少包含起始、结束与一个可执行的步 | Each procedure must contain at least a Start, an End and an executable step |
| -134436444 | ERROR_COMPILE_EMPTY_RIGHT_VALUE2 | 在右侧输入框中选择一个位号/参数/变量 | Please select a tag or parameter or variable on the right side |
| -133244331 | ERROR_COMPILE_INPUT_PARAM_ONLY | [{0}]仅支持使用输入参数 | [{0}]Only input parameter is supported |
| -130997696 | ERROR_COMPILE_REQUEST_REQ_HEAD_FIELD_CONTANS_CHINESE | 请求头字段含有中文 | Request head field contains Chinese characters |
| -128914379 | ERROR_COMPILE_PARAM_IO_TYPE | 参数[{0}]输入输出类型错误 | Parameter[{0}] IO type error |
| -128868185 | ERROR_COMPILE_PIN_NO_SUPPORT_ALIAS | 引脚[{0}]暂不支持绑定别名 | Pin[{0}] does not currently support binging Alias |
| -128254875 | ERROR_COMPILE_REQUEST_REPLY_FIELD_ILLEGAL | 响应字段[{0}]包含非法字符 | The response field [{0}] contains illegal characters |
| -128106930 | ERROR_COMPILE_FAILED_TO_WRITE_XLSX_FILE | xlsx写入文件失败 | Failed To Write xlsx File |
| -126946324 | ERROR_COMPILE_TARGET_VALUE_OUT_OF_RANGE | [{0}]右侧值范围应为{1} ~ {2} | [{0}]The value on the right side should be between {1} and {2} |
| -126741904 | ERROR_COMPILE_NONEXISTENT_TIMER | [{0}]不存在的计时器 | [{0}]Nonexisting timer |
| -126143065 | ERROR_COMPILE_INPUT_FORBIDDEN | 不允许有输入 | No input is allowed |
| -121020263 | ERROR_COMPILE_SAME_VALUE | [{0}]相同的左侧与右侧值 | [{0}]Left and right values are the same |
| -119718441 | ERROR_COMPILE_REQUEST_REPLY_FIELD_TOO_LONG | 响应字段层级超过{0} | Reply field cannot more than {0} |
| -119385226 | ERROR_COMPILE_MATERIAL_PARAM_ONLY | [{0}]仅支持使用物料参数 | [{0}]Only material parameter is supported |
| -118664610 | ERROR_COMPILE_NUMBERIC_VAR | [{0}]变量必须为数值类型 | [{0}]Variable must be of numberic type |
| -117658825 | ERROR_COMPILE_EMPTY_RIGHT_VALUE3 | 在右侧输入框中选择一个参数/变量 | Please select a parameter or variable in the box on the right side |
| -117234700 | ERROR_COMPILE_SCAN_CODE_PLACEHOLDER_EMPTY | 未选择占位变量 | Empty placeholder variable |
| -116780985 | ERROR_COMPILE_DUPLICATE_ALIAS | 别名重复 | Duplicate alias |
| -115516434 | ERROR_COMPILE_PROC_CMD_IN_TEMPLET | 模板中的子程序停止、子程序暂停只对当前程序生效 | SubStop/SubPause in template only affect current procedure |
| -115480863 | ERROR_COMPILE_INVALID_TAG_TYPE | [{0}]无效的位号 | [{0}]Invalid tag |
| -115395953 | ERROR_COMPILE_WRITE_VALUE_MULTI_TIMES | [{0}]无法在同一个步中重复写值 | [{0}]You can only write value once in a single step |
| -114910949 | ERROR_COMPILE_EMPTY_ENUM_PARAM | 未选择枚举参数 | Please select a enum param |
| -114614722 | ERROR_COMPILE_EMPTY_QUEUE_NAME_IN_SUBPROC | 分支[{0}]未选择运行设备 | Please select a run device first in Branch[{0}] |
| -114037859 | ERROR_COMPILE_OLD_PARAM_VAR_DATATYPE | [{0}]参数/变量的数据类型发生变动，请在输入框中重新选择 | [{0}]Data type has been changed, please reselect the parameter/variable in the box |
| -113405013 | ERROR_COMPILE_BRANCH_NOT_DATA | 分支{0}未配置数据 | Branch{0} has no data |
| -108804472 | ERROR_COMPILE_INVALID_WAIT_TYPE | 无效的等待类型 | Invalid wait type |
| -108777275 | ERROR_COMPILE_DEVICE_PARAM_NOT_ENUM | 配置的参数不是枚举类型 | Param not enum |
| -105185653 | ERROR_COMPILE_EMPTY_LEFT_PARAM | 在左侧输入框中选择一个参数 | Please select a parameter in the box on the left side |
| -105126193 | ERROR_COMPILE_DUPLICATE_ALIAS_STRUCT_NAME | [{0}]别名结构体名称重复 | [{0}]Duplicate alias struct name |
| -104244011 | ERROR_COMPILE_NONEXISTENT_ALIAS | [{0}]不存在的别名 | [{0}]Nonexisting alias |
| -103515297 | ERROR_COMPILE_FM_LINE_POS | {0}(位于行：{1}) | {0} Line: {1} |
| -103305847 | ERROR_COMPILE_NUMBERIC | [{0}]参数/变量类型必须为数值类型 | [{0}]Parameter/variable must be of numberic type |
| -102858887 | ERROR_COMPILE_FILE_PATH_NOT_EXIST | 文件路径不存在 | File Path is Not Exist |
| -102387411 | ERROR_COMPILE_FM_WRITE_TAG_VAR | 无法在FailMonitor的同一项中同时进行写位号与写变量操作 | Cannot write tag and write parameter/variable in a single FailMonitor item |
| -101870820 | ERROR_COMPILE_REPEATED_INPUT | 重复的输入 | Repeated input |
| -98944923 | ERROR_COMPILE_UNKNOWN_SUBPROC_COMMAND | 未配置子程序命令 | Unknowm subprocedure command |
| -97677076 | ERROR_COMPILE_NONEXETENT_SUBPROC | 子程序已发生变动，请重新编辑：{0} | Subprocedure is changed, please check: {0} |
| -97054196 | ERROR_COMPILE_DEFER_PARAM_MULTI_TIMES | [{0}]对同一个参数只能进行一次值传递 | [{0}]You can only deliver value to the same parameter once |
| -96694449 | ERROR_COMPILE_EMPTY_PIN_VALUE | 引脚[{0}]未绑定 | Pin[{0}] value can not be empty |
| -96338341 | ERROR_COMPILE_CONSTANT_DOUBLE_ILLEGAL | [{0}]浮点型常量最多允许{1}位 | [{0}]Float constants allow up to {1} digit |
| -93940024 | ERROR_COMPILE_EMPTY_CHECKED_TAG | 未选择被校验位号 | Empty checked tag |
| -92163486 | ERROR_COMPILE_EMPTY_ALIAS_STRUCT | [{0}]别名结构体为空 | [{0}]Empty alias struct |
| -91997916 | ERROR_COMPILE_EMPTY_LEFT_PARAM_VAR | 在左侧输入框中选择一个参数/变量 | Please select a parameter or variable in the box on the left side |
| -91371964 | ERROR_COMPILE_EMPTY_FILE_PARAM | 未添加任何参数 | No parameter added |
| -89907193 | ERROR_COMPILE_INVALID_VARIABLE_TYPE | [{0}]无效的参数/变量 | [{0}]Invalid parameter/variable type |
| -88217109 | ERROR_COMPILE_REPEATED_SUBPROC_NAME | 子程序名称重复 | Repeated subprocedure name |
| -87172646 | ERROR_COMPILE_INVALID_SIGN_PATH_ID | 无效的电子签名路径 | Invalid signature path |
| -85807555 | ERROR_COMPILE_ILLEGAL_WRITE_VALUE_MODE | 无效的写值模式 | Illegal write-value mode |
| -85467544 | ERROR_COMPILE_FORBIDDEN_END_IN_PARALLEL | 结束步不能出现在并行步中 | End Step is not allowed to be added into a Parallel Step |
| -84760221 | ERROR_COMPILE_TEMPLET_IN_NONRUNNING_PROCESS | 异常流程不能包含模板 | Abnormal process doesn't have templates |
| -84692981 | ERROR_COMPILE_DEVICE_TEMPLATE_INVALID | 设备模板步未选择有效的模板程序 | Device template step select invalid template procedure |
| -84355902 | ERROR_COMPILE_DEVICE_ENUM_PARAM_NOT_MATCH | 设备与枚举参数[{0}]不匹配 | Device and enum param [{0}] not match |
| -78918516 | ERROR_COMPILE_VAR_ENUM_BIND_EMPTY_RUN_QUEUE | 变量[{0}]关联的枚举集[{1}]的枚举[{2}]未关联设备 | The enumeration [{2}] in enum set [{1}] associated with variable [{0}] is not linked to any device |
| -78241047 | ERROR_COMPILE_EMPTY_TEMPLET_NAME | 模板名称不能为空 | Empty template name isn't allowed |
| -77550899 | ERROR_COMPILE_INVALID_CSV_DATA | 无效的csv数据 | Invalid Csv Data |
| -74702161 | ERROR_COMPILE_INTERSECTING_BRANCH | 分支存在交点：{0} | Branches crossed at {0} |
| -72854256 | ERROR_COMPILE_FAILED_TO_NO_SHEET | xlsx文件没有对应的sheet页 | Failed To Read  xlsx No Sheet |
| -72419776 | ERROR_COMPILE_SCAN_CODE_NOE_DATE_SET | 未配置校验数据 | Empty checking data |
| -72117401 | ERROR_COMPILE_EXCEEDED_SCAN_CODE_TIMES | 超过最大扫码次数 | Exceeded Scan Code Times |
| -70226910 | ERROR_COMPILE_REQUEST_REQ_BIND_VALUE_TYPE_INVALID | 绑定值[{0}]不允许为位号或别名 | Request bind value [{0}] type invalid |
| -68980586 | ERROR_COMPILE_OUTPUT_FORBIDDEN | 不允许有输出 | No output is allowed |
| -68671208 | ERROR_COMPILE_FILE_PATH_EMPTY | 文件路径为空 | File Path is Empty |
| -65406023 | ERROR_COMPILE_NONEXISTENT_TAG | [{0}]不存在的位号 | [{0}]Non-existing tag |
| -62732733 | ERROR_COMPILE_SCAN_CODE_UNKNOWN_STRATAGY | 未选择记录策略：{0} | Unknown strategy: {0} |
| -61128202 | ERROR_COMPILE_ENUM_EXCEED_UPPER_LIMIT | 枚举[{0}]超过写值上限 | Enumeration[{0}] exceeds upper limit |
| -60759119 | ERROR_COMPILE_STATUS_CHECK_EMPTY_STATUS | 状态检查步状态未配置 | Status check step status not configured |
| -60612329 | ERROR_COMPILE_PROCEDURE_STATUS_TYPE_ILLEGAL | 程序状态类型不合法 | Illegal procedure status type |
| -57821831 | ERROR_COMPILE_INVALID_SYSTEM_PARAM | [{0}]无效的预设变量 | [{0}]Invalid system parameter |
| -55580038 | ERROR_COMPILE_SUBPROC_IN_NONRUNNING_PROCESS | 异常流程不能包含子程序 | Abnormal process doesn't have subprocedure |
| -53028757 | ERROR_COMPILE_SCAN_CODE_RECORD_VALUE_EMPTY | 未选择记录值 | Empty record value |
| -52853790 | ERROR_COMPILE_SUBPROC_IN_TEMPLET | 模板不能包含子程序 | Subprocedure is not allowed in a template |
| -52583837 | ERROR_COMPILE_SELF_WRITE | [{0}]不可对自身写值 | [{0}]It cannot write value to itself |
| -52259326 | ERROR_COMPILE_EMPTY_LEFT_TAG | 在左侧输入框中选择一个位号 | Please select a tag in the box on the left side |
| -52149049 | ERROR_COMPILE_EMPTY_RIGHT_TAG | 在右侧输入框中选择一个位号 | Please select a tag in the box on the right side |
| -49257595 | ERROR_COMPILE_MIN_ONE_OUTPUT | 至少1路输出 | At least one channel of output is required |
| -48979203 | ERROR_COMPILE_SCAN_CODE_PLACEHOLDER_UNNAMED | 存在未命名的占位变量 | Unnamed placeholder variable |
| -47498295 | ERROR_COMPILE_EMPTY_QUEUE_NAME | 未选择运行设备 | Please select a run device first |
| -42386953 | ERROR_COMPILE_REQUEST_FIELD_ILLEGAL | 请求字段[{0}]包含非法字符 | The request field [{0}] contains illegal characters |
| -41750206 | ERROR_COMPILE_EXPRESS_LENGTH | 表达式的长度不超过{0}个字符 | The expression must not exceed a length of {0} characters including spaces |
| -39996416 | ERROR_COMPILE_PARAM_ENUM_BIND_MULTI_RUN_QUEUE | 参数[{0}]关联的枚举集[{1}]的枚举[{2}]被多个设备关联 | The enumeration [{2}] in enum set [{1}] associated with param [{0}] is linked to multiple device |
| -39344616 | ERROR_COMPILE_ALGORITHM_PINS_NEED_UPDATE | 算法模块[{0}]引脚有变更 | Algorithm module [{0}] pins need update |
| -37313940 | ERROR_COMPILE_XLSX_COL_EMPTY | csv/xlsx列名为空 | Empty Csv/Xlsx Col |
| -37207818 | ERROR_COMPILE_INVALID_VALUE_TYPE | [{0}]无效的位号/参数/变量 | [{0}]Invalid tag/parameter/variable type |
| -35675313 | ERROR_COMPILE_EMPTY_EXPRESS | 空的表达式 | Expression is empty |
| -35328673 | ERROR_COMPILE_ONE_OUTPUT | 有且只能有1路输出 | One and only one channel of output is required |
| -34899616 | ERROR_COMPILE_NONEXISTENT_VAR | [{0}]不存在的变量 | [{0}]Nonexisting variable |
| -33312293 | ERROR_COMPILE_INVALID_DATA_TYPE | [{0}]无效的数据类型 | [{0}]Invalid data type |
| -33159534 | ERROR_COMPILE_EMPTY_PARAM | 选择一个参数/变量 | Please select a parameter/variable |
| -31848101 | ERROR_COMPILE_EMPTY_TARGET_VALUE | 空的目标值 | Target value is empty |
| -31320284 | ERROR_COMPILE_EMPTY_DEVICE_MODEL | 程序模式不能为空 | Empty device model isn't allowed |
| -31297236 | ERROR_COMPILE_SCANCODE_EMPTY_CONTENT | 扫码的内容不允许为空 | Scan content cannot be empty |
| -31167389 | ERROR_COMPILE_EMPTY_TARGET_PARAM | 选择一个目标参数/变量 | Please select a target parameter/variable |
| -27441279 | ERROR_COMPILE_ALIAS_TAG_EMPTY | 别名或位号存在空值 | Alias or tag is empty |
| -26364037 | ERROR_COMPILE_EMPTY_MATERIAL_PARAM | 未选择物料参数 | Empty material parameter |
| -23740485 | ERROR_COMPILE_EMPTY_CONCAT_EXPRESSES | 未添加字符串拼接表达式 | No concat expression added |
| -23729506 | ERROR_COMPILE_ILLEGAL_TIME_RANGE | [{0}]时间范围不合法 | [{0}]Illegal time range |
| -23564834 | ERROR_COMPILE_SCAN_CODE_PLACEHOLDER_DATATYPE_UNSPECIFIED | 未设置占位变量[{0}]的数据类型 | Unspecified placeholder variable[{0}] data type |
| -22803796 | ERROR_COMPILE_NUMBERIC_SERVER_VARIABLE | [{0}]服务器变量类型必须为数值类型 | [{0}]Server variable must be of numberic type |
| -22443857 | ERROR_COMPILE_NONEXISTENT_SVR_VAR | [{0}]不存在的服务器变量 | [{0}]Nonexisting svrver variable |
| -22230244 | ERROR_COMPILE_PARAM_ENUM_BIND_EMPTY_RUN_QUEUE | 参数[{0}]关联的枚举集[{1}]的枚举[{2}]未关联设备 | The enumeration [{2}] in enum set [{1}] associated with param [{0}] is not linked to any device |
| -18762285 | ERROR_COMPILE_ONE_END | 程序有且只能有1个结束步 | Each procedure have and only have one single End Step |
| -18173705 | ERROR_COMPILE_DEVICE_EMPTY_ENUM_PARAM | 枚举参数未配置 | Enum param not configured |
| -17491014 | ERROR_COMPILE_INVALID_ALIAS_CONTENT | [{0}]别名仅支持位号 | [{0}]Alias only support tag |
| -16484264 | ERROR_COMPILE_EMPTY_ACTUAL_VALUE | 未选择实际投料量参数 | Empty actual value parameter |
| -15478972 | ERROR_COMPILE_VAR_BIND_MULTI_DEVICE_ENUM_SET | 变量[{0}]关联的枚举集[{1}]被多个设备绑定 | The enumeration set [{1}] associated with variable [{0}] is bound to multiple devices |
| -14671538 | ERROR_COMPILE_DEVICE_TYPE_NOT_EXIST | 设备类型[{0}]不存在 | Device type [{0}] not exist |
| -13807187 | ERROR_COMPILE_SCAN_CODE_PLACEHOLDER_UNUSED | 未使用的占位变量：{0} | Unused placeholder variable: {0} |
| -13477989 | ERROR_COMPILE_DEAL_FILE_TIMEOUT | 处理文件超时 | Deal File Time Out |
| -13066123 | ERROR_COMPILE_EMPTY_SELECTION | 未配置选择数据 | No selection configuration found |
| -10344955 | ERROR_COMPILE_INTERSECTING_BRANCH_IN_PARALLEL | 平行分支存在交点：{0} | Branches crossed at {0} |
| -10106768 | ERROR_COMPILE_EMPTY_QUEUE_OR_EMPTY_QUEUE_JUDGE | 运行设备未配置或运行设备条件未配置 | Run device empty or empty judge for device |
| -8974845 | ERROR_COMPILE_RELATION_TYPE_INVALID | 无效的条件关系类型 | Invalid conditional relation type |
| -8956786 | ERROR_COMPILE_SCAN_CODE_CHECK_VALUE_EMPTY | 未选择校验值 | Empty checking value |
| -8447142 | ERROR_COMPILE_UNKNOWN_CONSTANT_TYPE | [{0}]未知的常量数据类型 | [{0}]Unknown constant data type |
| -7296101 | ERROR_COMPILE_QUEUE_AUTO_RELEASE | 推荐选择自动释放 | Auto-release is recommended |
| -5927603 | ERROR_COMPILE_SCAN_CODEPLACEHOLDER_TYPE | 占位变量[{0}]的数据类型与内部占位变量数据类型不一致 | The data type of placeholder variable[{0}] is not compatible with inner placeholder variable's |
| -5232440 | ERROR_COMPILE_NONEXISTENT_PARAM | [{0}]不存在的参数 | [{0}]Nonexisting parameter |
| -5027961 | ERROR_COMPILE_PARAM_ONLY | [{0}]仅支持使用参数 | [{0}]Only parameter is supported |
| -4041080 | ERROR_COMPILE_COMMON_STR | {0} | {0} |
| -3030983 | ERROR_COMPILE_EMPTY_CLOCK_DATA | 时钟时间为空 | Clock configuration is empty |
