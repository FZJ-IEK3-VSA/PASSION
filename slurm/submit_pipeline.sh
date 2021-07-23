#!/bin/bash

#SBATCH --output="logs/slurm-%x-%A-%a.out"
#SBATCH --job-name=pipeline
#SBATCH --nodes=1
#SBATCH --cpus-per-task=10
#SBATCH --partition=simulus

#### JOB LOGIC ###
export OMP_NUM_THREADS=6
export USE_SIMPLE_THREADED_LEVEL3=1
export MKL_NUM_THREADS=1

source activate passion-test

# If you would like to run the script
# sbatch submit_run_my_example.sh

# If you would like to run the script more than once for different parameters
# sbatch -a 0-2 submit_run_my_example.sh

python pipeline.py $SLURM_ARRAY_TASK_ID
