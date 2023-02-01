#Datasets="wiki"
Datasets="vec"
#Datasets="wiki epinions twitter"
#Programs="reach"
#Programs="cc"
Programs="presum_stratified"
# Programs="cc reach sssp"

function qry ()
{
	case "$1" in
		"reach") Sfx="" ;;
		"cc") Sfx="" ;;
		"sssp") Sfx="-w" ;;
		*) echo "bad program";;
	esac
	return 0
}

function runrs ()
{
	python3 quickstep_shell.py --mode network &
	time python3 interpreter.py ./benchmark_datalog_programs/$1$Opt.datalog
	echo "select count(*) from $1;" | python3 quickstep_shell.py --mode interactive
}

for P in $Programs
do
	qry $P
	for D in $Datasets
	do
		cp ../datasets/$D/$D$Sfx.csv ./Input/arc.csv
		echo " BENCHMARKING $P on $D" ;
		#cp Config.json.t Config.json
		#Opt=""
		#runrs $P
		cp Config.json.f Config.json
		Opt="-opt"
		runrs $P
	done
done
