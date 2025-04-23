#ifndef SYMMETRY_H
#define SYMMETRY_H

#include <string>
#include <vector>

using std::string;

class Symmetry {
 public:
  Symmetry(int w, int h) : w_(w), h_(h) {}

  // Returns the canonical version of the board (possibly the input board).
  string Canonicalize(const string& board);

 private:
  // Basic symmetries applied to board strings
  string FlipY(const string& bd);
  string FlipX(const string& bd);
  string Rotate90CW(const string& bd);

  // Conversions between indices and coordinates.
  inline int Id(int x, int y) const { return x * h_ + y; }
  inline int X(int id) const { return id / h_; }
  inline int Y(int id) const { return id % h_; }

  int w_;
  int h_;
};

#endif  // SYMMETRY_H
