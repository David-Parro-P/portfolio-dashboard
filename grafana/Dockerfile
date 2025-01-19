FROM grafana/grafana:10.2.3
RUN grafana-cli plugins install frser-sqlite-datasource
USER root
RUN chown -R grafana:root /var/lib/grafana/plugins
USER grafana