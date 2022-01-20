FROM python:3.6.4
RUN mkdir /code
WORKDIR /code
COPY . /code
COPY requirements.txt /code
COPY run.sh /code
RUN pip install -r /code/requirements.txt -i https://pypi.douban.com/simple

CMD ["/bin/bash", "/code/run.sh"]