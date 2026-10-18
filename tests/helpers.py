import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\n"


def record(gene, star, rsid, gt, extra=""):
    return f"chr1\t100\t{rsid}\tC\tT\t99\tPASS\tRS={rsid};GENE={gene};STAR={star}{extra}\tGT:DP\t{gt}:30\n"


def make_vcf(*records):
    return HEADER + "".join(records)


def sample(name):
    with open(os.path.join(ROOT, name)) as f:
        return f.read()
