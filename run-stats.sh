#! /bin/sh
./factory.py --users=users openSUSE:Factory
csv=`ls *.csv | tail -3 | head -1`
dat=`echo $csv | cut -d. -f1`
./fixtable.py $csv > result-$dat.txt

echo "Automatic Factory stats for week $dat" | mail -s "Factory stats for week $dat" -a result-$dat.txt -r aplanas@suse.de -R aplanas@suse.de rd-ops-cm@suse.de jpoortvliet@suse.de

