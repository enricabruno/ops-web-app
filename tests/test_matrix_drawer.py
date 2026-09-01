"""Round-trip del drawer di approfondimento in /explain: riaprire e
richiudere il pannello deve riportare il grafico esattamente com'era (non
"quasi") - stesso viewBox, stessa larghezza renderizzata, stessa marca
fissata.

Test di integrazione via browser reale (Playwright): serve un server
Flask in ascolto su http://localhost:5001, con una costrizione che abbia
almeno una cella con più di una costrizione (per poter fissare una
selezione cliccandola) e almeno una nota (storica o ambito) che renda
visibile il drawer. Esegui con:
    python3 -m unittest tests/test_matrix_drawer.py
"""
import unittest

from playwright.sync_api import sync_playwright

BASE_URL = 'http://localhost:5001'
CONSTRAINT_URI = 'https://w3id.org/desmos/prisoner_constraint'
EXPLAIN_URL = f'{BASE_URL}/explain?uri={CONSTRAINT_URI}'

# viewBox nativo dei due preset (constraint_matrix.js, layoutFor): usarne la
# larghezza per riconoscere il preset evita di dover esporre lo stato
# interno del modulo JS al test.
COMODO_NATIVE_WIDTH = 1082
COMPATTO_NATIVE_WIDTH = 824


class MatrixDrawerRoundTripTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={'width': 1400, 'height': 900})
        # Il richiamo all'arrivo (pulse + nudge, una tantum per sessione) non
        # è oggetto di questo test e introdurrebbe un'animazione extra da
        # attendere: lo si disattiva simulando una sessione già "vista".
        self.page.add_init_script(
            "try { sessionStorage.setItem('ops.drawerSeen', '1'); } catch (e) {}"
        )
        self.page.goto(EXPLAIN_URL)
        self.page.wait_for_selector('#constraint-matrix-viz svg', timeout=10000)
        self.page.wait_for_timeout(200)

    def tearDown(self):
        self.page.close()

    def _viz_state(self):
        svg = self.page.query_selector('#constraint-matrix-viz svg')
        viewbox = svg.get_attribute('viewBox')
        width = self.page.query_selector('#constraint-matrix-viz').bounding_box()['width']
        return viewbox, width

    def _preset_name(self):
        viewbox, _ = self._viz_state()
        native_width = float(viewbox.split()[2])
        if native_width == COMODO_NATIVE_WIDTH:
            return 'comodo'
        if native_width == COMPATTO_NATIVE_WIDTH:
            return 'compatto'
        self.fail(f'viewBox nativo inatteso: {viewbox}')

    def _fixed_selection_uri(self):
        """URI del primo vincolo elencato nel pannello risultati per la
        selezione correntemente fissata, o None se non c'e' nulla di
        fissato."""
        link = self.page.query_selector('#constraint-matrix-results .matrix-results-flow a')
        if link is None:
            return None
        return link.get_attribute('href')

    def _wait_panel_settled(self):
        """Attende la fine della transizione CSS del pannello (transform in
        overlay, width in regime push) più un margine di sicurezza: un
        ResizeObserver con debounce puo' catturare una larghezza intermedia
        durante l'animazione, non quella finale."""
        self.page.evaluate("""
            () => new Promise((resolve) => {
                const panel = document.querySelector('.matrix-drawer__panel');
                let done = false;
                const finish = () => {
                    if (done) return;
                    done = true;
                    panel.removeEventListener('transitionend', finish);
                    resolve();
                };
                panel.addEventListener('transitionend', finish);
                setTimeout(finish, 1000); // rete di sicurezza se transitionend non arriva
            })
        """)
        self.page.wait_for_timeout(200)

    def _open_drawer(self):
        self.page.click('#matrix-drawer-handle')
        self._wait_panel_settled()

    def _close_drawer(self):
        self.page.click('#matrix-drawer-handle')
        self._wait_panel_settled()

    def test_round_trip_preserves_viewbox_width_and_selection(self):
        # 1. stato iniziale
        viewbox_before, width_before = self._viz_state()
        self.assertEqual(self._preset_name(), 'comodo')

        # 2. fissa una selezione cliccando una marca di gruppo (n > 1)
        group_mark = self.page.query_selector('.matrix-mark--group')
        self.assertIsNotNone(
            group_mark, 'serve almeno una marca con n > 1 per poter fissare una selezione')
        group_mark.click()
        self.page.wait_for_timeout(100)
        fixed_uri = self._fixed_selection_uri()
        self.assertIsNotNone(fixed_uri, 'il clic sulla marca di gruppo non ha fissato nulla')

        # 3-4. apri il drawer, attendi transitionend + 200ms, registra viewBox e larghezza
        self._open_drawer()
        viewbox_open, width_open = self._viz_state()
        self.assertEqual(self._preset_name(), 'compatto')
        self.assertNotEqual(viewbox_open, viewbox_before)
        self.assertLess(width_open, width_before)

        # 5-6. chiudi il drawer, attendi transitionend + 200ms, registra viewBox e larghezza
        self._close_drawer()
        viewbox_after, width_after = self._viz_state()

        self.assertEqual(viewbox_after, viewbox_before, 'viewBox non ripristinato esattamente')
        self.assertEqual(width_after, width_before, 'larghezza non ripristinata esattamente')
        self.assertEqual(self._preset_name(), 'comodo')
        self.assertEqual(
            self._fixed_selection_uri(), fixed_uri,
            'la selezione fissata prima dell\'apertura non e\' piu\' quella attiva dopo la chiusura')

    def test_round_trip_survives_rapid_toggles(self):
        """Cinque cicli apri/chiudi rapidi e consecutivi: il debounce del
        ResizeObserver non deve lasciare uno stato incoerente (preset
        sbagliato, o una larghezza intermedia mai corretta dopo l'ultimo
        resize)."""
        viewbox_before, width_before = self._viz_state()
        self.assertEqual(self._preset_name(), 'comodo')

        handle = self.page.query_selector('#matrix-drawer-handle')
        for _ in range(5):
            handle.click()
            self.page.wait_for_timeout(40)  # più veloce del debounce (150ms) e della transizione (300ms)
            handle.click()
            self.page.wait_for_timeout(40)

        # Il drawer torna chiuso (numero pari di clic): lascia che l'ultima
        # transizione e l'ultimo debounce si esauriscano del tutto.
        self.page.wait_for_timeout(600)

        viewbox_after, width_after = self._viz_state()
        self.assertEqual(viewbox_after, viewbox_before)
        self.assertEqual(width_after, width_before)
        self.assertEqual(self._preset_name(), 'comodo')
        self.assertEqual(self.page.get_attribute('#matrix-drawer', 'data-open'), 'false')


if __name__ == '__main__':
    unittest.main()
