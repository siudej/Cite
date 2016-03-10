#/bin/bash

CURRENT=`pwd`
PYTHON=`find ~/anaconda* -d 0 2> /dev/null || echo "/usr"`

tee /usr/local/bin/cite <<EOF
#!/bin/bash
export PATH="\$PATH:/Library/TeX/texbin:/usr/texbin"
cd $CURRENT
$PYTHON/bin/python cite.py \$@
EOF

chmod +x /usr/local/bin/cite

for filename in ./osx/*.workflow; do
    cp -R "$filename" ./
done

for filename in *.workflow; do
    open "$filename"
done
