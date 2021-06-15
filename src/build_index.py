import argparse
from bsbi import *

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--size', type=int, default='10240', help='Memory block size in KB')
parser.add_argument('-d', '--dir', type=str, default='dataset', help='Path to directory with text corpus')

args = parser.parse_args()

# Размер блока устанавливается в КБ, но индексатор принимает его в Байтах
args.size *= 1024

worker = BSBI(args.dir, args.size)
worker.build_index()
