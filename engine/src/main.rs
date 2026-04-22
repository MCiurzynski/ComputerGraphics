use core::panic;
use glam::{DMat4, DVec4};
use minifb::{Key, Window, WindowOptions, KeyRepeat};
use rfd::FileDialog;
use std::{f64::consts::PI, fs::File};
use std::time::{SystemTime, UNIX_EPOCH};

const WIDTH: usize = 1000; // Window constants
const HEIGHT: usize = 1000;
const FOCAL_LENGTH: f64 = 100.0;

#[derive(Clone, Copy, Debug)] // Struct containing color
struct Color {
    red: u8,
    green: u8,
    blue: u8,
}

impl Color {
    fn encode(&self) -> u32 {
        // encoder for buffer
        u32::from_le_bytes([self.blue, self.green, self.red, 0])
    }

    fn white() -> Self {
        // White color constructor
        Self {
            red: 255,
            green: 255,
            blue: 255,
        }
    }
}

struct Polygon {
    points: Vec<DVec4>,
    color: Color,
}

impl Polygon {
    // Methods for line
    fn normalize(&mut self) {
        // Points normalization in polygon
        for point in self.points.iter_mut() {
            *point = *point / point.w;
        }
        
    }

    fn transform(&mut self, matrix: DMat4) {
        // Applying transformation matrix to line points
        for point in self.points.iter_mut() {
            *point = matrix * *point;
        }
        self.normalize();
    }

    fn cast(&self, d: f64) -> Polygon {
        // Casting line to z axis plane
        let mut cast_matrix = DMat4::IDENTITY;
        cast_matrix.w_axis.w = 0.0;
        cast_matrix.z_axis.w = 1.0 / d;

        let mut casted_points: Vec<DVec4> = Vec::new();
        for point in self.points.iter() {
            let mut casted = cast_matrix * point;
            if casted.w != 0.0 {
                casted = casted / casted.w;
            }
            casted.x += WIDTH as f64 / 2.0;
            casted.y += HEIGHT as f64 / 2.0;
            casted_points.push(casted);
        }

        Polygon {
            points: casted_points,
            color: self.color,
        }
    }
    fn load(path: &str) -> Vec<Polygon> {
        use std::io::{BufRead, BufReader};

        // Otwieramy plik, używamy BufReader dla lepszej wydajności czytania linia po linii
        let file = File::open(path).expect("Nie można otworzyć pliku OBJ");
        let reader = BufReader::new(file);

        let mut vertices: Vec<DVec4> = Vec::new();
        let mut polygons: Vec<Polygon> = Vec::new();

        for line in reader.lines() {
            let line = line.expect("Błąd podczas czytania linii");
            let mut tokens = line.split_whitespace();

            match tokens.next() {
                Some("v") => {
                    // Parsowanie wierzchołków
                    let x: f64 = tokens.next().unwrap_or("0").parse().unwrap_or(0.0);
                    let y: f64 = tokens.next().unwrap_or("0").parse().unwrap_or(0.0);
                    let z: f64 = tokens.next().unwrap_or("0").parse().unwrap_or(0.0);
                    
                    // Współrzędna w = 1.0 dla punktów w przestrzeni 3D
                    vertices.push(DVec4::new(x, y, z, 1.0));
                }
                Some("f") => {
                    // Parsowanie ścian (wielokątów)
                    let mut points = Vec::new();
                    for token in tokens {
                        // Format ściany to często "v/vt/vn", interesuje nas tylko pierwszy element "v"
                        let v_index_str = token.split('/').next().unwrap_or("1");
                        
                        if let Ok(v_index) = v_index_str.parse::<usize>() {
                            // Format OBJ indeksuje od 1, więc musimy odjąć 1 dla tablicy w Ruście
                            if v_index > 0 && v_index <= vertices.len() {
                                points.push(vertices[v_index - 1]);
                            }
                        }
                    }
                    
                    // Jeśli udało się zebrać punkty, tworzymy nowy Polygon
                    if !points.is_empty() {
                        polygons.push(Polygon {
                            points,
                            color: Color::white(), // Używamy domyślnego, białego koloru z Twojego konstruktora
                        });
                    }
                }
                _ => {} // Ignorujemy komentarze (#), normalne (vn), tekstury (vt) itp.
            }
        }

        polygons
    }
}

fn get_translation_matrix(x: f64, y: f64, z: f64) -> DMat4 {
    // Creating translation matrix
    let mut m: DMat4 = DMat4::IDENTITY;
    m.w_axis.x = x;
    m.w_axis.y = y;
    m.w_axis.z = z;
    m
}

fn get_rotation_matrix(x: f64, y: f64, z: f64) -> DMat4 {
    // Creating rotation matrix
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

enum Transform {
    // Base transformations
    TranslateX(f64),
    TranslateY(f64),
    TranslateZ(f64),
    RotateX(f64),
    RotateY(f64),
    RotateZ(f64),
}

impl Transform {
    // Matching transformations enum to matrixes
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
        // Bresenham algorithm implementation
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

    fn draw_polygon(&mut self, polygon: &Polygon) {
        let casted = polygon.cast(self.focal_length);
        for pair in casted.points.windows(2) {
            self.draw_line_from_points(&pair[0], &pair[1], &polygon.color);
        }
    }

    fn draw_polygons(&mut self, polygons: &[Polygon]) {
        for polygon in polygons.iter() {
            self.draw_polygon(polygon);
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
        // keyboard handling
        let mut matrix = DMat4::IDENTITY;
        if self.is_key_down(Key::A) {
            matrix = Transform::TranslateX(2.0).matrix() * matrix;
        }
        if self.is_key_down(Key::D) {
            matrix = Transform::TranslateX(-2.0).matrix() * matrix;
        }
        if self.is_key_down(Key::W) {
            matrix = Transform::TranslateZ(-1.0).matrix() * matrix;
        }
        if self.is_key_down(Key::S) {
            matrix = Transform::TranslateZ(1.0).matrix() * matrix;
        }
        if self.is_key_down(Key::Space) {
            matrix = Transform::TranslateY(2.0).matrix() * matrix;
        }
        if self.is_key_down(Key::LeftShift) {
            matrix = Transform::TranslateY(-2.0).matrix() * matrix;
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

    fn save_screenshot(&self, path: &str) {
        let width = self.width as u32;
        let height = self.height as u32;
        let mut img_buffer = vec![0u8; (width * height * 3) as usize];

        for (i, &pixel) in self.buffer.iter().enumerate() {
            let bytes = pixel.to_le_bytes(); 
            
            img_buffer[i * 3] = bytes[2];
            img_buffer[i * 3 + 1] = bytes[1];
            img_buffer[i * 3 + 2] = bytes[0];
        }

        match image::save_buffer(path, &img_buffer, width, height, image::ColorType::Rgb8) {
            Ok(_) => println!("File saved: {}", path),
            Err(e) => println!("Error during saving file: {}", e),
        }
    }
}

fn main() {
    let file = FileDialog::new()
        .set_title("Select file")
        .add_filter("OBJ models", &["obj"])
        .pick_file();

    let path = match file {
        Some(path) => path.display().to_string(),
        None => {
            println!("File not selected");
            return;
        }
    };

    let mut vec = Polygon::load(&path);

    let mut screen = Screen::new();
    screen.set_target_fps(60);

    while screen.is_open() && !screen.is_key_down(Key::Escape) {
        let matrix = screen.transform_matrix();
        for polygon in vec.iter_mut() {
            polygon.transform(matrix);
        }
        screen.scroll_handling();
        
        if screen.window.is_key_pressed(Key::Enter, KeyRepeat::No) {
            let start = SystemTime::now();
            let since_the_epoch = start.duration_since(UNIX_EPOCH).unwrap();
            let filename = format!("screenshot_{}.png", since_the_epoch.as_millis());
            
            screen.save_screenshot(&filename);
        }
        screen.clear();
        screen.draw_polygons(&vec);
        screen.update();
    }
}
