# ForensicStack — generic triage scanner
#
# Deliberately minimal: stdlib-only Python, no pip install, no build tools in
# the final image. The scanner parses hostile input, so its blast radius should
# be as close to "an interpreter and a script" as possible.
FROM python:3.11-slim

# Non-root by default. The platform also passes --user, but an image that is
# only safe because the caller remembered a flag is not a safe image.
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin forensic

COPY tool/triage_scan.py /opt/triage/triage_scan.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod 0555 /opt/triage/triage_scan.py /entrypoint.sh

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER forensic
WORKDIR /tmp

ENTRYPOINT ["/entrypoint.sh"]
