FROM python:3.12-slim-bookworm
EXPOSE 8000
USER root
RUN apt-get update && apt-get install -y php supervisor php-curl wget 
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt
RUN wget -O chrome.deb "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"  
RUN chmod +x chrome.deb
RUN dpkg -i chrome.deb || apt-get -f install -y
COPY flag.txt /flag.txt
WORKDIR /app
COPY challenge /app
COPY config/supervisord.conf /etc/supervisord.conf
CMD  ["/usr/bin/supervisord", "-c" ,"/etc/supervisord.conf"]
