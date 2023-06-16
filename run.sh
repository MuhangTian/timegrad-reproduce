#!/bin/bash
#SBATCH --job-name=traffic
#SBATCH --time=1-00:00:00
#SBATCH --partition=gpu-common
#SBATCH --gres=gpu:RTX2080:1
#SBATCH --mem=25G
#SBATCH --mail-user=muhang.tian@duke.edu
#SBATCH --output=reproduce_traffic.out
#SBATCH --mail-type=END
#SBATCH --mail-type=FAIL

conda init bash
conda activate ts
srun python reproduce.py --dataset traffic_nips --save reproduce_traffic.png --input_size 3856