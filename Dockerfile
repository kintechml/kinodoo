FROM bitnami/odoo:17.0.20241005-debian-12-r0

RUN cd /opt/bitnami/odoo && \
     venv/bin/pip3 install reportlab[renderPM] \
