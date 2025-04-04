import subprocess

def run_install():
    subprocess.run([
        "pip", "install",
        "torch", "torchaudio", "torchvision",
        "--find-links=https://mirror.sjtu.edu.cn/pytorch-wheels/torch_stable.html",
        "--no-index"
    ], check=True)