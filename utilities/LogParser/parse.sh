if [ -z "$1" ]
then
    file="/var/log/httpd/ssl_access_log"
else
    file=$1
fi
grep pdf $file | awk '{print $4  $7}' | awk 'BEGIN{FS="/"} {print $1 "/" $2 "/" $3 "_" $5 "_" $6}' | awk 'BEGIN{FS="_"} {$NF=""; print $0}'  >> output | sort | uniq > output
