# Simple 3D engine

The project aims to create a simple 3D graphics rendering engine. The prototype is written in Python using the NumPy library (for matrix calculations) and the Pygame library (for basic display and control).
The main engine is written in Rust. It uses minifb library to create windows and handle control and glam library for matrix multiplication.

## Prototype
To launch prototype you need to write following commands to terminal after downloading repository. You'll also need uv package manager to create venv.
```
cd prototype
uv sync
uv run main.py
```

## Engine
To compile engine you need to write following commands. You'll also need cargo to compile project.

```
cd engine
cargo build --release
```