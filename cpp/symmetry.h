#ifndef SYMMETRY_H
#define SYMMETRY_H

#include <string>
#include <vector>

class Symmetry {
 public:
  Symmetry(int w, int h) : w_(w), h_(h) {}

  // Returns the canonical version of the board (possibly the input board).
  std::string Canonicalize(const std::string& board);

 private:
  // Basic symmetries applied to board strings
  std::string FlipY(const std::string& bd);
  std::string FlipX(const std::string& bd);
  std::string Rotate90CW(const std::string& bd);

  // Conversions between indices and coordinates.
  inline int Id(int x, int y) const { return x * h_ + y; }
  inline int X(int id) const { return id / h_; }
  inline int Y(int id) const { return id % h_; }

  int w_;
  int h_;
};

#endif  // SYMMETRY_H
