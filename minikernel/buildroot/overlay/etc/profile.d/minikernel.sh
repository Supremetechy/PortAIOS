#!/bin/sh
# MiniKernel environment setup

export MINIKERNEL_HOME=/opt/minikernel
export PYTHONPATH=$MINIKERNEL_HOME:$PYTHONPATH
export PATH=$MINIKERNEL_HOME/bin:$PATH

# Welcome message
cat << 'EOF'

  __  __ _       _ _  __                    _ 
 |  \/  (_)     (_) |/ /                   | |
 | \  / |_ _ __  _| ' / ___ _ __ _ __   ___| |
 | |\/| | | '_ \| |  < / _ \ '__| '_ \ / _ \ |
 | |  | | | | | | | . \  __/ |  | | | |  __/ |
 |_|  |_|_|_| |_|_|_|\_\___|_|  |_| |_|\___|_|
                                              
 AI-First Voice-Controlled Operating System
 Type 'minikernel' to start the voice interface
 Type 'minikernel-cli' for command-line mode

EOF

# Convenience aliases
alias minikernel='python3 -m minikernel.boot'
alias minikernel-cli='python3 -m minikernel.boot --mode=cli'
alias minikernel-logs='tail -f /var/log/minikernel.log'
alias minikernel-status='systemctl status minikernel'
