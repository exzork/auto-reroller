# FMJP Templates Directory

This directory should contain template images for button/UI element recognition.

## Required Templates:
- `start_button.png` - Template for the start button
- `loop_button.png` - Template for the loop/continue button

## Template Guidelines:
- Use PNG format for best quality
- Screenshot the exact button/element you want to detect
- Keep templates small and focused on the specific element
- Test templates with different screen resolutions if needed

## Adding New Templates:
1. Take a screenshot of the UI element
2. Crop to just the element you want to detect
3. Save as PNG in this directory
4. Update the template names in `fmjp_game.py` automation states
5. Add threshold values in `config.json` if needed 