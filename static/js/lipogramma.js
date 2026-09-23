(function () {
  // Evidenziazione ipotesto → ipertesto per il lipogramma (sezione #lipo-texts).
  // Selettori limitati al contenitore: non interferisce con anagrafia.js.
  const box = document.getElementById('lipo-texts');
  if (!box) return;

  box.querySelectorAll('.lipo-src-tok[data-targets]').forEach(src => {
    const targets = src.dataset.targets.split(' ').filter(Boolean)
      .map(i => box.querySelector(`.lipo-tgt-tok[data-idx="${i}"]`))
      .filter(Boolean);
    const toggle = on => {
      src.classList.toggle('lipo-active', on);
      targets.forEach(t => t.classList.toggle('lipo-active', on));
    };
    src.addEventListener('mouseenter', () => toggle(true));
    src.addEventListener('mouseleave', () => toggle(false));
    src.addEventListener('focus',      () => toggle(true));
    src.addEventListener('blur',       () => toggle(false));
  });
})();
