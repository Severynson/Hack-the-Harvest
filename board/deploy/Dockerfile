# Hugging Face Space (Docker SDK) for the Kernel model board. No GPU needed.
FROM python:3.12-slim
# git pulls the team repo; libexpat1 is needed by the GDAL inside the rasterio wheel (live "silage or grain?" lookups).
RUN apt-get update && apt-get install -y --no-install-recommends git libexpat1 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH \
    BOARD_PORT=7860 BOARD_AUTOPULL=5 \
    REPO_URL=https://github.com/Severynson/Hack-the-Harvest.git DATA_BRANCH=hackathon-2026-submission BOARD_BRANCH=board
WORKDIR /home/user
RUN pip install --no-cache-dir --user "pandas>=2.2" "numpy>=1.26" pyarrow fastapi "uvicorn>=0.30" geopandas \
    pystac-client planetary-computer "rasterio>=1.4"
COPY --chown=user start.sh /home/user/start.sh
EXPOSE 7860
CMD ["bash", "/home/user/start.sh"]
