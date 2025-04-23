#include "symmetry.h"

std::string Symmetry::Canonicalize(const std::string& board) {
  if (board.size() != w_ * h_) return "";
  std::string best = board;
  std::string bd;
  bd = FlipX(board);
  if (bd < best) best = bd;
  bd = FlipY(bd);
  if (bd < best) best = bd;
  bd = FlipX(bd);
  if (bd < best) best = bd;

  if (w_ == h_) {
    bd = Rotate90CW(board);
    if (bd < best) best = bd;
    bd = FlipX(bd);
    if (bd < best) best = bd;
    bd = FlipY(bd);
    if (bd < best) best = bd;
    bd = FlipX(bd);
    if (bd < best) best = bd;
  }

  return best;
}

std::string Symmetry::FlipY(const std::string& bd) {
  if (bd.size() != w_ * h_) return "";
  std::string out(w_ * h_, ' ');
  for (int y = 0; y < h_; y++) {
    for (int x = 0; x < w_; x++) {
      out[Id(x, y)] = bd[Id(x, h_ - 1 - y)];
    }
  }
  return out;
}

std::string Symmetry::FlipX(const std::string& bd) {
  if (bd.size() != w_ * h_) return "";
  std::string out(w_ * h_, ' ');
  for (int x = 0; x < w_; x++) {
    for (int y = 0; y < h_; y++) {
      out[Id(x, y)] = bd[Id(w_ - 1 - x, y)];
    }
  }
  return out;
}

std::string Symmetry::Rotate90CW(const std::string& bd) {
  if (w_ != h_) return "";  // rotation only works for square boards!
  std::string out(w_ * h_, ' ');
  for (int x = 0; x < w_; x++) {
    for (int y = 0; y < h_; y++) {
      out[Id(w_ - 1 - y, x)] = bd[Id(x, y)];
    }
  }
  return out;
}
