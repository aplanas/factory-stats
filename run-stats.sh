#! /bin/sh
./factory-commits.py --users=users openSUSE:Factory
csv="last-week.csv"
dat=`date +"%Y-%m-%d"`
./fixtable.py $csv > result-$dat.txt

echo "Automatic Factory stats for week $dat" | mail -s "Factory stats for week $dat" -a result-$dat.txt -r aplanas@suse.de -R aplanas@suse.de rd-ops-cm@suse.de jpoortvliet@suse.de

gzip result-$dat.txt
