if [ -z "$1" ]
then
    file="/var/log/httpd/ssl_access_log"
else
    file=$1
fi
    
if [ -f output ]
then
    grep pdf $file | sed -n -e "/$(tail -n 1 output | awk '{print $1}' | cut -c 2- | awk 'BEGIN{FS="/"} {print $3}')/,\$p" | tail -n +2 | awk '{print $4  $7}' | awk 'BEGIN{FS="/"} {print $1 "/" $2 "/" $3 "_" $5 "_" $6}' | awk 'BEGIN{FS="_"} {$NF=""; print $0}'  >> output
else
    grep pdf $1 | awk '{print $4  $7}' | awk 'BEGIN{FS="/"} {print $1 "/" $2 "/" $3 "_" $5 "_" $6}' | awk 'BEGIN{FS="_"} {$NF=""; print $0}'  >> output
fi
