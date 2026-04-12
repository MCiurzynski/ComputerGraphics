use core::panic;
use std::{f64::consts::PI, fs::File, io::Read, path::Path};

use glam::{DMat4, DVec4};

const WIDTH: usize = 1000;
const HEIGHT: usize = 1000;
const FOCAL_LENGTH: f64 = 100.0;

use minifb::{Key, Window, WindowOptions};

#[derive(Clone, Copy, Debug)]
struct Color {
    red: u8,
    green: u8,
    blue: u8,
}

impl Color {
    fn encode(&self) -> u32 {
        u32::from_le_bytes([self.blue, self.green, self.red, 0])
    }

    fn white() -> Self {
        Self {
            red: 255,
            green: 255,
            blue: 255,
        }
    }
}

struct Line {
    start: DVec4,
    end: DVec4,
    color: Color,
}

impl Line {
    fn new(x0: f64, y0: f64, z0: f64, x1: f64, y1: f64, z1: f64, color: Color) -> Self {
        Self {
            start: DVec4::new(x0, y0, z0, 1.0),
            end: DVec4::new(x1, y1, z1, 1.0),
            color: color,
        }
    }

    fn normalize(&mut self) {
        self.start = self.start / self.start.w;
        self.end = self.end / self.end.w;
    }

    fn transform(&mut self, matrix: DMat4) {
        self.start = matrix * self.start;
        self.end = matrix * self.end;
        self.normalize();
    }

    fn cast(&self, d: f64) -> Line {
        let mut cast_matrix = DMat4::IDENTITY;
        cast_matrix.w_axis.w = 0.0;
        cast_matrix.z_axis.w = 1.0 / d;
        let translation_matrix =
            get_translation_matrix(WIDTH as f64 / 2.0, HEIGHT as f64 / 2.0, 0.0);
        let matrix = translation_matrix * cast_matrix;
        let mut casted = Line {
            start: matrix * self.start,
            end: matrix * self.end,
            color: self.color,
        };
        casted.normalize();
        casted
    }

    fn load(path: &str) -> Vec<Line> {
        let path = Path::new(path);
        let display = path.display();
        let mut file = match File::open(&path) {
            Err(why) => panic!("Couldn't open {display}, {why}"),
            Ok(file) => file,
        };
        let mut content = String::new();
        match file.read_to_string(&mut content) {
            Err(why) => panic!("Couldn't open {display}, {why}"),
            Ok(_) => (),
        }
        let mut lines: Vec<Line> = Vec::new();
        for line in content.lines() {
            let coords: Vec<f64> = line
                .split_whitespace()
                .map(|c| c.parse().unwrap())
                .collect();
            let line = Line::new(
                coords[0],
                coords[1],
                coords[2],
                coords[3],
                coords[4],
                coords[5],
                Color::white(),
            );
            lines.push(line);
        }
        lines
    }
}

enum Transform {
    TranslateX(f64),
    TranslateY(f64),
    TranslateZ(f64),
    RotateX(f64),
    RotateY(f64),
    RotateZ(f64),
}

fn get_translation_matrix(x: f64, y: f64, z: f64) -> DMat4 {
    let mut m: DMat4 = DMat4::IDENTITY;
    m.w_axis.x = x;
    m.w_axis.y = y;
    m.w_axis.z = z;
    m
}

fn get_rotation_matrix(x: f64, y: f64, z: f64) -> DMat4 {
    let mut x_rotation: DMat4 = DMat4::IDENTITY;
    x_rotation.y_axis.y = f64::cos(x);
    x_rotation.y_axis.z = f64::sin(x);
    x_rotation.z_axis.y = -f64::sin(x);
    x_rotation.z_axis.z = f64::cos(x);

    let mut y_rotation: DMat4 = DMat4::IDENTITY;
    y_rotation.x_axis.x = f64::cos(y);
    y_rotation.x_axis.z = -f64::sin(y);
    y_rotation.z_axis.x = f64::sin(y);
    y_rotation.z_axis.z = f64::cos(y);

    let mut z_rotation: DMat4 = DMat4::IDENTITY;
    z_rotation.x_axis.x = f64::cos(z);
    z_rotation.x_axis.y = f64::sin(z);
    z_rotation.y_axis.x = -f64::sin(z);
    z_rotation.y_axis.y = f64::cos(z);
    x_rotation * y_rotation * z_rotation
}

impl Transform {
    fn matrix(self) -> DMat4 {
        match self {
            Transform::TranslateX(step) => get_translation_matrix(step, 0.0, 0.0),
            Transform::TranslateY(step) => get_translation_matrix(0.0, step, 0.0),
            Transform::TranslateZ(step) => get_translation_matrix(0.0, 0.0, step),
            Transform::RotateX(rad) => get_rotation_matrix(rad, 0.0, 0.0),
            Transform::RotateY(rad) => get_rotation_matrix(0.0, rad, 0.0),
            Transform::RotateZ(rad) => get_rotation_matrix(0.0, 0.0, rad),
        }
    }
}

struct Screen {
    buffer: Vec<u32>,
    width: i32,
    height: i32,
    window: Window,
    focal_length: f64,
}

impl Screen {
    fn is_open(&self) -> bool {
        self.window.is_open()
    }

    fn set_target_fps(&mut self, fps: usize) {
        self.window.set_target_fps(fps);
    }

    fn is_key_down(&self, key: Key) -> bool {
        self.window.is_key_down(key)
    }

    fn update(&mut self) {
        self.window
            .update_with_buffer(&self.buffer, self.width as usize, self.height as usize)
            .unwrap()
    }

    fn set_pixel(&mut self, x: i32, y: i32, color: &Color) {
        let i = x + y * self.width;
        if i >= 0 && i < self.width * self.height && x < self.width && y < self.height {
            self.buffer[i as usize] = color.encode();
        }
    }

    fn clear(&mut self) {
        self.buffer.fill(0);
    }

    fn draw_low(&mut self, x0: i32, y0: i32, x1: i32, y1: i32, color: &Color) {
        let dx = x1 - x0;
        let mut dy = y1 - y0;
        let mut yi: i32 = 1;
        if dy < 0 {
            yi = -1;
            dy = -dy;
        }
        let mut d = 2 * dy - dx;
        let mut y = y0;

        for i in x0..x1 + 1 {
            self.set_pixel(i, y, &color);
            if d > 0 {
                y += yi;
                d += 2 * (dy - dx);
            } else {
                d += 2 * dy;
            }
        }
    }

    fn draw_high(&mut self, x0: i32, y0: i32, x1: i32, y1: i32, color: &Color) {
        let mut dx = x1 - x0;
        let dy = y1 - y0;
        let mut xi: i32 = 1;
        if dx < 0 {
            xi = -1;
            dx = -dx;
        }
        let mut d = 2 * dx - dy;
        let mut x = x0;

        for i in y0..y1 + 1 {
            self.set_pixel(x, i, &color);
            if d > 0 {
                x += xi;
                d += 2 * (dx - dy);
            } else {
                d += 2 * dx;
            }
        }
    }

    fn draw_line(&mut self, x0: i32, y0: i32, x1: i32, y1: i32, color: &Color) {
        if (y1 - y0).abs() < (x1 - x0).abs() {
            if x0 > x1 {
                self.draw_low(x1, y1, x0, y0, color);
            } else {
                self.draw_low(x0, y0, x1, y1, color);
            }
        } else {
            if y0 > y1 {
                self.draw_high(x1, y1, x0, y0, color);
            } else {
                self.draw_high(x0, y0, x1, y1, color);
            }
        }
    }
    fn draw_line_from_points(&mut self, start: &DVec4, end: &DVec4, color: &Color) {
        let max_coord = 20_000.0;
        if start.x.abs() > max_coord
            || start.y.abs() > max_coord
            || end.x.abs() > max_coord
            || end.y.abs() > max_coord
        {
            return;
        }
        let x0: i32 = start.x as i32;
        let y0: i32 = start.y as i32;
        let x1: i32 = end.x as i32;
        let y1: i32 = end.y as i32;
        self.draw_line(x0, y0, x1, y1, color);
    }

    fn draw_line_from_line(&mut self, line: &Line) {
        let casted = line.cast(self.focal_length);
        self.draw_line_from_points(&casted.start, &casted.end, &casted.color);
    }

    fn draw_line_from_vec(&mut self, vec: &[Line]) {
        for line in vec {
            self.draw_line_from_line(&line);
        }
    }

    fn new() -> Self {
        let window = Window::new("3D Engine", WIDTH, HEIGHT, WindowOptions::default())
            .unwrap_or_else(|e| {
                panic!("{}", e);
            });
        Self {
            buffer: vec![0; WIDTH * HEIGHT],
            width: WIDTH as i32,
            height: HEIGHT as i32,
            window: window,
            focal_length: FOCAL_LENGTH,
        }
    }

    fn transform_matrix(&self) -> DMat4 {
        let mut matrix = DMat4::IDENTITY;
        if self.is_key_down(Key::A) {
            matrix = Transform::TranslateX(1.0).matrix() * matrix;
        }
        if self.is_key_down(Key::D) {
            matrix = Transform::TranslateX(-1.0).matrix() * matrix;
        }
        if self.is_key_down(Key::W) {
            matrix = Transform::TranslateZ(-1.0).matrix() * matrix;
        }
        if self.is_key_down(Key::S) {
            matrix = Transform::TranslateZ(1.0).matrix() * matrix;
        }
        if self.is_key_down(Key::Space) {
            matrix = Transform::TranslateY(1.0).matrix() * matrix;
        }
        if self.is_key_down(Key::LeftShift) {
            matrix = Transform::TranslateY(-1.0).matrix() * matrix;
        }
        if self.is_key_down(Key::E) {
            matrix = Transform::RotateZ(-PI / 90.0).matrix() * matrix;
        }
        if self.is_key_down(Key::Q) {
            matrix = Transform::RotateZ(PI / 90.0).matrix() * matrix;
        }
        if self.is_key_down(Key::Up) {
            matrix = Transform::RotateX(PI / 90.0).matrix() * matrix;
        }
        if self.is_key_down(Key::Down) {
            matrix = Transform::RotateX(-PI / 90.0).matrix() * matrix;
        }
        if self.is_key_down(Key::Right) {
            matrix = Transform::RotateY(-PI / 90.0).matrix() * matrix;
        }
        if self.is_key_down(Key::Left) {
            matrix = Transform::RotateY(PI / 90.0).matrix() * matrix;
        }
        matrix
    }

    fn scroll_handling(&mut self) {
        let scroll_option = self.window.get_scroll_wheel();
        if let Some((_, y)) = scroll_option {
            if self.focal_length + y as f64 > 0.0 {
                self.focal_length += y as f64;
            }
        }
    }
}

fn main() {
    let mut screen = Screen::new();
    screen.set_target_fps(60);

    let mut vec = Line::load("../assets/rubik2x2x2.txt");

    while screen.is_open() && !screen.is_key_down(Key::Escape) {
        let matrix = screen.transform_matrix();
        for line in vec.iter_mut() {
            line.transform(matrix);
        }
        screen.scroll_handling();
        screen.clear();
        screen.draw_line_from_vec(&vec);
        screen.update();
    }
}
