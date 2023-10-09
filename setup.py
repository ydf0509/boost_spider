# coding=utf-8
from setuptools import setup, find_packages

setup(
    name='boost_siper',  #
    version='0.9',
    description=(
        '横冲直闯 自由奔放 无回调 无继承写法的高速爬虫框架'
    ),
    # long_description=open('README.md', 'r',encoding='utf8').read(),
    keywords=["scrapy", "funboost", "distributed-framework", "function-scheduling", "rabbitmq", "rocketmq", "kafka",
              "nsq", "redis",
              "sqlachemy", "consume-confirm", "timing", "task-scheduling", "apscheduler", "pulsar", "mqtt", "kombu",
              "的", "celery",
              "框架", '分布式调度'],
    long_description_content_type="text/markdown",
    long_description=open('README.md', 'r', encoding='utf8').read(),
    author='bfzs',
    author_email='ydf0509@sohu.com',
    maintainer='ydf',
    maintainer_email='ydf0509@sohu.com',
    license='BSD License',
    packages=find_packages(),
    include_package_data=True,
    platforms=["all"],
    url='https://github.com/ydf0509/boost_spider',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Libraries'
    ],
    install_requires=[
        'funboost',
        'universal_object_pool',
        'pymysql',
        'pymongo',
        'parsel',
        'requests',
    ],

)

"""
官方 https://pypi.org/simple
清华 https://pypi.tuna.tsinghua.edu.cn/simple
豆瓣 https://pypi.douban.com/simple/ 
阿里云 https://mirrors.aliyun.com/pypi/simple/
腾讯云  http://mirrors.tencentyun.com/pypi/simple/

打包上传
python setup.py sdist upload -r pypi

python setup.py sdist & python -m twine upload dist/boost_siper-0.9.tar.gz

"""
