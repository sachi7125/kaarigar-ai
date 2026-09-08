// Custom on-screen numeric keypad — digits only, no letters, no OS keyboard
// (wireframe: "Numeric keypad next — digits, no letters", "Minimum touch
// target drawn at 64 px"). Used for phone entry and OTP entry, both of which
// must work for someone who cannot read a QWERTY layout. (Day 5)
import 'package:flutter/material.dart';

const _accent = Color(0xFF4F46E5);

class NumericKeypad extends StatelessWidget {
  final String value;
  final int maxLength;
  final ValueChanged<String> onChanged;

  const NumericKeypad({
    Key? key,
    required this.value,
    required this.maxLength,
    required this.onChanged,
  }) : super(key: key);

  void _tapDigit(String d) {
    if (value.length >= maxLength) return;
    onChanged(value + d);
  }

  void _backspace() {
    if (value.isEmpty) return;
    onChanged(value.substring(0, value.length - 1));
  }

  @override
  Widget build(BuildContext context) {
    const rows = [
      ['1', '2', '3'],
      ['4', '5', '6'],
      ['7', '8', '9'],
      ['', '0', '⌫'],
    ];
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: rows.map((row) {
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: row.map((key) {
              if (key.isEmpty) return const SizedBox(width: 76, height: 64);
              final isBackspace = key == '⌫';
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 6),
                child: Material(
                  color: isBackspace ? const Color(0xFFF3F4F6) : Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  elevation: 1,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(16),
                    onTap: () => isBackspace ? _backspace() : _tapDigit(key),
                    child: SizedBox(
                      width: 76,
                      height: 64,
                      child: Center(
                        child: isBackspace
                            ? const Icon(Icons.backspace_outlined, color: Color(0xFF6B7280), size: 24)
                            : Text(key, style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w600, color: Color(0xFF1F2937))),
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        );
      }).toList(),
    );
  }
}

/// Row of boxes showing entered digits (●) vs empty slots (○) — a visual
/// progress indicator that needs no reading, matching the wireframe's rule
/// that nothing essential exists only as text.
class DigitDots extends StatelessWidget {
  final int entered;
  final int total;
  const DigitDots({Key? key, required this.entered, required this.total}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(total, (i) {
        final filled = i < entered;
        return Container(
          width: 16, height: 16,
          margin: const EdgeInsets.symmetric(horizontal: 6),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: filled ? _accent : Colors.transparent,
            border: Border.all(color: _accent, width: 2),
          ),
        );
      }),
    );
  }
}
