/**
 * Iris — AR Overlay (ar_overlay.js)
 * Draws directional navigation arrows on the camera canvas.
 */

const AROverlay = (() => {
  let canvas, ctx;
  let currentSteps = [];   // NavigationStep[]
  let currentStepIndex = 0;
  let animFrame = null;
  let animPhase = 0;

  // Arrow colors
  const ARROW_COLOR   = 'rgba(124, 58, 237, 0.95)';  // iris purple
  const ARROW_GLOW    = 'rgba(167, 139, 250, 0.5)';
  const ARROW_OUTLINE = 'rgba(255, 255, 255, 0.85)';

  function init(canvasElement) {
    canvas = canvasElement;
    ctx    = canvas.getContext('2d');
    _resizeCanvas();
    window.addEventListener('resize', _resizeCanvas);
  }

  function _resizeCanvas() {
    if (!canvas) return;
    canvas.width  = canvas.offsetWidth  || window.innerWidth;
    canvas.height = canvas.offsetHeight || window.innerHeight;
  }

  /**
   * Set navigation steps and start drawing.
   * @param {Array} steps - Array of NavigationStep objects
   */
  function setNavigation(steps) {
    currentSteps     = steps || [];
    currentStepIndex = 0;
    if (currentSteps.length > 0) {
      _startAnimation();
    } else {
      clearNavigation();
    }
  }

  function clearNavigation() {
    currentSteps     = [];
    currentStepIndex = 0;
    if (animFrame) {
      cancelAnimationFrame(animFrame);
      animFrame = null;
    }
    if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  function advanceStep() {
    if (currentStepIndex < currentSteps.length - 1) {
      currentStepIndex++;
    } else {
      clearNavigation();
    }
  }

  function _startAnimation() {
    if (animFrame) cancelAnimationFrame(animFrame);
    function loop() {
      animPhase += 0.03;
      _drawFrame();
      animFrame = requestAnimationFrame(loop);
    }
    loop();
  }

  function _drawFrame() {
    if (!ctx || currentSteps.length === 0) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const step = currentSteps[currentStepIndex];
    const cx   = canvas.width  / 2;
    const cy   = canvas.height / 2;

    // Animated float offset
    const floatY = Math.sin(animPhase) * 8;

    _drawArrow(cx, cy + floatY, step.direction);
    _drawStepLabel(cx, cy + floatY + 90, step.distance, step.instruction);
  }

  function _drawArrow(cx, cy, direction) {
    ctx.save();
    ctx.translate(cx, cy);

    // Rotate based on direction
    const rotations = {
      'straight':     0,
      'left':        -Math.PI / 2,
      'right':        Math.PI / 2,
      'sharp-left':  -Math.PI * 0.75,
      'sharp-right':  Math.PI * 0.75,
      'slight-left': -Math.PI / 4,
      'slight-right': Math.PI / 4,
      'u-turn':       Math.PI,
      'roundabout':   Math.PI / 4,
      'fork-left':   -Math.PI / 3,
      'fork-right':   Math.PI / 3,
      'merge':        0,
      'ramp-left':   -Math.PI / 4,
      'ramp-right':   Math.PI / 4,
    };
    const angle = rotations[direction] ?? 0;
    ctx.rotate(angle);

    const size = 56;

    // Glow halo
    const gradient = ctx.createRadialGradient(0, 0, size * 0.3, 0, 0, size * 1.4);
    gradient.addColorStop(0, 'rgba(167, 139, 250, 0.35)');
    gradient.addColorStop(1, 'rgba(124, 58, 237, 0)');
    ctx.beginPath();
    ctx.arc(0, 0, size * 1.4, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();

    // Circle background
    ctx.beginPath();
    ctx.arc(0, 0, size, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(10, 10, 15, 0.7)';
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = ARROW_COLOR;
    ctx.stroke();

    // Arrow shape
    ctx.beginPath();
    ctx.moveTo(0, -size * 0.55);       // tip (pointing up = "straight")
    ctx.lineTo(size * 0.35, size * 0.25);
    ctx.lineTo(size * 0.15, size * 0.25);
    ctx.lineTo(size * 0.15, size * 0.55);
    ctx.lineTo(-size * 0.15, size * 0.55);
    ctx.lineTo(-size * 0.15, size * 0.25);
    ctx.lineTo(-size * 0.35, size * 0.25);
    ctx.closePath();

    ctx.fillStyle = ARROW_COLOR;
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = ARROW_OUTLINE;
    ctx.stroke();

    ctx.restore();
  }

  function _drawStepLabel(cx, cy, distance, instruction) {
    const maxWidth = Math.min(canvas.width * 0.8, 400);

    // Background pill
    const textH = 68;
    const textW = maxWidth;
    const x = cx - textW / 2;
    const y = cy - textH / 2;

    ctx.save();
    ctx.beginPath();
    ctx.roundRect(x, y, textW, textH, 12);
    ctx.fillStyle = 'rgba(10, 10, 15, 0.75)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(124, 58, 237, 0.5)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Distance
    ctx.font = 'bold 18px "Space Grotesk", sans-serif';
    ctx.fillStyle = '#a78bfa';
    ctx.textAlign = 'center';
    ctx.fillText(distance || '', cx, cy - 6);

    // Instruction
    ctx.font = '13px Inter, sans-serif';
    ctx.fillStyle = 'rgba(241, 245, 249, 0.9)';
    const truncated = (instruction || '').length > 50
      ? instruction.slice(0, 48) + '…'
      : instruction;
    ctx.fillText(truncated, cx, cy + 18);

    ctx.restore();
  }

  // Public API
  return { init, setNavigation, clearNavigation, advanceStep };
})();
