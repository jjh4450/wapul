use std::io::{self, Read, Write};

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).unwrap();
    let mut it = input.split_ascii_whitespace().map(|x| x.parse::<i64>().unwrap());
    let n = it.next().unwrap();
    let mut total = 0;
    let mut best = i64::MIN;
    for _ in 0..n {
        let x = it.next().unwrap();
        total += x;
        if x > best {
            best = x;
        }
    }
    let out = io::stdout();
    let mut out = out.lock();
    match total % 2 {
        0 => writeln!(out, "even {}", best).unwrap(),
        _ => writeln!(out, "odd {}", best).unwrap(),
    }
}
