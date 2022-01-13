## Python虚拟环境Usage

```
0.安装virtualenv
	pip3 install virtualenv 
1.创建目录
	mkdir Test
	cd Test
2.创建独立运行环境-命名venv
	virtualenv --python=python3  venv0
3.进入虚拟环境
	source venv0/bin/activate
4.安装第三方包
	pip3 install geven
	pip3 install alive_progress
	pip3 install requests
5. 正确运行
	python3 morePing.py -v
6. 导出依赖包
	pip3 freeze > requirements.txt
6.退出venv环境
	deactivate
```

