FROM python:3.12-slim

WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --system postnode && useradd --system --gid postnode --home-dir /service postnode
COPY --chown=postnode:postnode app app
COPY --chown=postnode:postnode data data
COPY --chown=postnode:postnode config config
RUN mkdir -p outputs && chown postnode:postnode outputs

USER postnode

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
