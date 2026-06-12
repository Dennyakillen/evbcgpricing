# =====================================================================
# run_status.py -- Statusfil-kontrakt for Phase Z (evbcgpricing)
# ---------------------------------------------------------------------
# Utvecklare: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
# Skapad:     Phase Z, session 1 (AI-radgivare)
#
# SYFTE
#   Definiera EN enda sanning om hur korstatus representeras. Bade
#   orchestratorn (azure_vm.py) som SKRIVER status, och Flask-frontytan
#   som LASER den, importerar denna modul. Da kan de aldrig tolka
#   falten olika -- vilket annars kollapsar hela polling-designen.
#
# VARFOR ETT KONTRAKT (designprincipen)
#   SSE ar kosmetik; sanningen om "lever korningen?" ar denna statusfil.
#   Den skrivs till Blob (inte bara VM) sa att den OVERLEVER att VM:en
#   deallokeras och kan lasas av en kollega UTAN VM-access. Detta ar
#   anledningen till att kontraktet ar serialiserbart till ren JSON och
#   inte beror pa nagot VM-lokalt tillstand.
#
# DESIGNVAL: faser bar VAR de kors (vm/local)
#   Pipelinens steg 5 + Step 6 ar Excel/COM-bundna och kors LOKALT pa
#   Windows (LB.44), inte pa Linux-VM:en. Darfor maste statuskontraktet
#   klara att vissa faser kors pa VM och vissa lokalt -- annars skulle
#   frontytan tro att korningen dott nar den i sjalva verket vantar pa
#   ett lokalt Excel-steg. Faltet 'location' pa varje fas loser detta.
#
# BEROENDEN
#   - Endast Python-standardbibliotek (json, datetime, dataclasses, enum).
#   - Blob-I/O ligger MEDVETET INTE har -- det hor till blob.py (Z.2).
#     Denna modul producerar/konsumerar enbart dict/JSON-strangar, sa
#     den kan enhetstestas helt utan Azure. blob.py limmar ihop.
#
# DETTA BEROR PA DEN
#   - azure_vm.py (skriver heartbeat + fasovergangar)
#   - Flask-frontytan / routes (laser och visar)
#   - ev. ett lokalt wrapper-script for steg 5/Step 6 som ocksa
#     uppdaterar status nar Excel-stegen kors pa Windows
#
# STANDARD
#   Tidsstamplar i UTC ISO-8601 med 'Z'-suffix -- entydigt mellan VM
#   (Linux/UTC) och din Windows-maskin. Frontytan far lokalisera vid
#   visning, aldrig vid lagring.
# =====================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------
# Versionering av sjalva kontraktet. Bumpas om faltformen andras, sa att
# en gammal frontyta kan vagra tolka en nyare statusfil i stallet for att
# gissa fel. "Mat, gissa inte" -- aven mellan komponentversioner.
# ---------------------------------------------------------------------
CONTRACT_VERSION = "1.0"


def utcnow_iso() -> str:
    """UTC-tidsstampel, ISO-8601 med Z. Enda tillatna tidsformatet i filen."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_duration(seconds: Optional[int]) -> Optional[str]:
    """Sekunder -> lasbar strang for loggen. Ex: 11532 -> '3h 12m 12s'.
    Tar med timmar bara nar de finns, sa korta steg blir '4m 30s' / '45s'."""
    if seconds is None:
        return None
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m or h:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


class RunState(str, Enum):
    """Overgripande livscykel for hela korningen (grovkornigt)."""
    PENDING    = "pending"     # bestalld, VM annu ej startad
    STARTING   = "starting"    # VM startar / git pull pagar
    RUNNING    = "running"     # minst en fas kor aktivt
    WAITING    = "waiting"     # vantar pa manuellt/lokalt steg (t.ex. Excel pa Windows)
    SUCCEEDED  = "succeeded"   # alla faser klara, output i Blob
    FAILED     = "failed"      # ngn fas foll; se 'error'
    DEALLOCATED= "deallocated" # VM nedstangd efter avslut (kan kombineras m. succeeded/failed historiskt)


class PhaseState(str, Enum):
    """Tillstand for en enskild fas (steg 1-6 m.fl.)."""
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCEEDED = "succeeded"
    FAILED    = "failed"
    SKIPPED   = "skipped"      # t.ex. bundle parkerad (FD.11)


class PhaseLocation(str, Enum):
    """VAR fasen kors. Avgor om frontytan ska vanta pa VM eller pa lokal maskin."""
    VM    = "vm"        # kors pa bcg-poc-vm (Linux), tunga modellsteg 1-4
    LOCAL = "local"     # kors pa Jens Windows-maskin (Excel/COM, steg 5 + Step 6)


@dataclass
class Phase:
    """En fas i pipelinen. 'key' ar stabil identifierare som frontytan kan
    rita progress mot; 'name' ar mansklig etikett."""
    key: str                                  # ex: "step1_dataprep", "step5_excel", "step6_fallback"
    name: str                                 # ex: "Steg 1 -- dataprep"
    location: PhaseLocation                   # vm | local
    state: PhaseState = PhaseState.PENDING
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    note: Optional[str] = None                # ex: rader producerade, KEY-antal

    @property
    def duration_seconds(self) -> Optional[int]:
        """Hur lange fasen tog (finished - started), i sekunder. None om
        fasen inte bade startat och slutat. Detta ar REN korytid for steget
        -- ingen pausetid ingar (en fas har inga pauser internt)."""
        if not (self.started_at and self.finished_at):
            return None
        t0 = datetime.strptime(self.started_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        t1 = datetime.strptime(self.finished_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return int((t1 - t0).total_seconds())

    @property
    def duration_human(self) -> Optional[str]:
        """Lasbar varaktighet for loggen, t.ex. '3h 12m' eller '4m 30s'."""
        s = self.duration_seconds
        return _fmt_duration(s) if s is not None else None


@dataclass
class RunStatus:
    """Hela statusobjektet som serialiseras till JSON och laggs i Blob.

    Falt som STARTPROMPT explicit kraver:
      - fas (vilket av steg 1-6)        -> current_phase_key + phases[]
      - starttid                        -> started_at
      - senaste heartbeat               -> last_heartbeat
      - slutstatus                      -> state + error
    """
    # Identitet / sparbarhet
    run_id: str                               # ex: "2026-06-12T0800Z" eller GUID
    contract_version: str = CONTRACT_VERSION
    git_sha: Optional[str] = None             # vilken commit VM:en korde (vag B, source of truth = Git)
    triggered_by: Optional[str] = None        # kollega/konto som tryckte kor

    # Overgripande tillstand
    state: RunState = RunState.PENDING
    started_at: Optional[str] = None
    last_heartbeat: Optional[str] = None      # uppdateras periodiskt sa frontytan ser liv
    finished_at: Optional[str] = None

    # Fasspar
    current_phase_key: Optional[str] = None
    phases: list[Phase] = field(default_factory=list)

    # Fel + output
    error: Optional[str] = None               # satt vid state=FAILED
    output_blob_paths: list[str] = field(default_factory=list)  # var kollegan hamtar resultatet

    # VM-livscykel (informativt for frontytan)
    vm_power_state: Optional[str] = None      # "running" | "deallocated" | ...

    # -------------------- Tidssummering (Jens onskemal) --------------------
    # Tva olika matt -- medvetet atskilda for att de svarar pa olika fragor:
    #   total_active_seconds : SUMMAN av varje stegs egen korytid. Ren
    #       berakningstid. Svarar pa "hur mycket jobb gjordes / var gar
    #       tiden?". Pauser mellan steg (klick, PIM, lokala Excel-steg)
    #       ingar INTE.
    #   wall_clock_seconds   : forsta stegets start -> sista stegets slut.
    #       Inkluderar pauser. Svarar pa "hur lange tog korningen totalt
    #       fran start till mal?".
    # Mat, gissa inte -- aven pa vad 'tid' betyder.

    @property
    def total_active_seconds(self) -> int:
        """Summan av alla avslutade stegs varaktigheter (ren korytid)."""
        return sum(p.duration_seconds or 0 for p in self.phases)

    @property
    def total_active_human(self) -> str:
        return _fmt_duration(self.total_active_seconds) or "0s"

    @property
    def wall_clock_seconds(self) -> Optional[int]:
        """Forsta start -> sista slut (inkl pauser). None om inget steg
        startat. Anvander sista AVSLUTADE stegets finished_at; om korningen
        pagar anvands last_heartbeat som 'hittills'."""
        starts = [p.started_at for p in self.phases if p.started_at]
        if not starts:
            return None
        t0 = min(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ") for s in starts)
        ends = [p.finished_at for p in self.phases if p.finished_at]
        if ends:
            t1 = max(datetime.strptime(e, "%Y-%m-%dT%H:%M:%SZ") for e in ends)
        elif self.last_heartbeat:
            t1 = datetime.strptime(self.last_heartbeat, "%Y-%m-%dT%H:%M:%SZ")
        else:
            return None
        return int((t1 - t0).total_seconds())

    @property
    def wall_clock_human(self) -> Optional[str]:
        return _fmt_duration(self.wall_clock_seconds)

    def timing_summary(self) -> str:
        """Loggvanlig sammanfattning av tidtagningen. Skrivs till loggfilen
        efter varje steg och vid korningens slut. Ren ASCII for PS-loggar.

        FOKUS (Jens motiv): den AKTIVA korytiden -- summan av stegens egen
        beraktid -- visar modellens KOMPLEXITET och ar huvudsiffran. Pauser
        mellan steg (klick/PIM) ar brus i det sammanhanget. Vaggklockan
        finns kvar som diskret fotnot for den som anda undrar, men den ar
        medvetet nedtonad sa att 'aktiv korytid' ar det som syns."""
        lines = ["Aktiv korytid per steg (ren beraktid -- visar modellens komplexitet):"]
        for p in self.phases:
            if p.duration_human:
                lines.append(f"  {p.name:<32} {p.duration_human}")
            elif p.state == PhaseState.RUNNING:
                lines.append(f"  {p.name:<32} (kor nu)")
            elif p.state == PhaseState.SKIPPED:
                lines.append(f"  {p.name:<32} (hoppad)")
        lines.append("  " + "-" * 44)
        lines.append(f"  {'SUMMA AKTIV KORYTID':<32} {self.total_active_human}")
        wc = self.wall_clock_human
        if wc:
            lines.append(f"  (vaggklocka inkl pauser, ej modelltid: {wc})")
        return "\n".join(lines)

    # -------------------- Serialisering --------------------
    def to_json(self) -> str:
        """Serialisera till indenterad JSON (lasbar i Blob-portalen ocksa).
        Berakade tidsfalt bakas in sa att en frontyta som bara laser JSON
        (utan denna kod) anda ser varaktigheter -- de skrivs explicit."""
        d = asdict(self)
        # Injicera berakade falt i serialiseringen (properties foljer ej med asdict).
        for i, p in enumerate(self.phases):
            d["phases"][i]["duration_seconds"] = p.duration_seconds
            d["phases"][i]["duration_human"] = p.duration_human
        d["total_active_seconds"] = self.total_active_seconds
        d["total_active_human"] = self.total_active_human
        d["wall_clock_seconds"] = self.wall_clock_seconds
        d["wall_clock_human"] = self.wall_clock_human
        def _enc(o):
            if isinstance(o, Enum):
                return o.value
            raise TypeError(f"Ej serialiserbar typ: {type(o)}")
        return json.dumps(d, default=_enc, ensure_ascii=False, indent=2)

    @staticmethod
    def from_json(s: str) -> "RunStatus":
        """Las tillbaka. Vagrar tolka okand kontraktsversion (mat, gissa inte)."""
        d = json.loads(s)
        ver = d.get("contract_version")
        if ver != CONTRACT_VERSION:
            raise ValueError(
                f"Statusfilens kontraktsversion '{ver}' matchar inte denna kods "
                f"'{CONTRACT_VERSION}'. Uppdatera komponenten i stallet for att gissa."
            )
        phases = [
            Phase(
                key=p["key"], name=p["name"],
                location=PhaseLocation(p["location"]),
                state=PhaseState(p["state"]),
                started_at=p.get("started_at"),
                finished_at=p.get("finished_at"),
                note=p.get("note"),
            )
            for p in d.get("phases", [])
        ]
        return RunStatus(
            run_id=d["run_id"],
            contract_version=ver,
            git_sha=d.get("git_sha"),
            triggered_by=d.get("triggered_by"),
            state=RunState(d.get("state", "pending")),
            started_at=d.get("started_at"),
            last_heartbeat=d.get("last_heartbeat"),
            finished_at=d.get("finished_at"),
            current_phase_key=d.get("current_phase_key"),
            phases=phases,
            error=d.get("error"),
            output_blob_paths=d.get("output_blob_paths", []),
            vm_power_state=d.get("vm_power_state"),
        )

    # -------------------- Mutationer (anvands av azure_vm.py) --------------------
    def beat(self) -> None:
        """Uppdatera heartbeat. Anropas periodiskt under langa faser sa
        frontytan ser att korningen lever aven om en fas tar timmar."""
        self.last_heartbeat = utcnow_iso()

    def start_phase(self, key: str) -> None:
        self.current_phase_key = key
        self.state = RunState.RUNNING
        now = utcnow_iso()
        for p in self.phases:
            if p.key == key:
                p.state = PhaseState.RUNNING
                p.started_at = now
        self.beat()

    def finish_phase(self, key: str, ok: bool = True, note: Optional[str] = None) -> None:
        now = utcnow_iso()
        for p in self.phases:
            if p.key == key:
                p.state = PhaseState.SUCCEEDED if ok else PhaseState.FAILED
                p.finished_at = now
                if note:
                    p.note = note
        self.beat()

    def mark_waiting(self, reason: str) -> None:
        """Satt nar pipelinen overlamnar till ett lokalt/manuellt steg (LB.44).
        Frontytan visar 'vantar' -- INTE 'dod'."""
        self.state = RunState.WAITING
        self.error = None
        # Aterbruka 'note' pa aktuell fas for orsak om sadan finns
        if self.current_phase_key:
            for p in self.phases:
                if p.key == self.current_phase_key:
                    p.note = reason
        self.beat()

    def fail(self, error: str) -> None:
        self.state = RunState.FAILED
        self.error = error
        self.finished_at = utcnow_iso()
        self.beat()

    def succeed(self, output_blob_paths: Optional[list[str]] = None) -> None:
        self.state = RunState.SUCCEEDED
        self.finished_at = utcnow_iso()
        if output_blob_paths:
            self.output_blob_paths = output_blob_paths
        self.beat()


# ---------------------------------------------------------------------
# Fabrik: standardpipeline for evbcgpricing. EN plats dar pipelinens
# faser och deras kor-plats definieras. Justera key/location har om
# kedjan andras -- bade orchestrator och frontyta foljer automatiskt.
#
# OBS: location pa step5/step6 ar satt till LOCAL enligt LB.44. Om
# Excel-stegen lyfts till headless (openpyxl utan COM) pa VM -- andra
# bara location till VM har, sa foljer resten med.
# ---------------------------------------------------------------------
def default_pipeline(run_id: str, git_sha: Optional[str] = None,
                     triggered_by: Optional[str] = None) -> RunStatus:
    phases = [
        Phase("extraction",     "Extraction (DW -> parquet)",       PhaseLocation.VM),
        Phase("step1_dataprep", "Steg 1 -- SQL data prep",          PhaseLocation.VM),
        Phase("step2_feature",  "Steg 2 -- feature selection",      PhaseLocation.VM),
        Phase("step3_model",    "Steg 3 -- modell (Ray)",           PhaseLocation.VM),
        Phase("step4_summary",  "Steg 4 -- output_summary",         PhaseLocation.VM),
        Phase("step5_excel",    "Steg 5 -- Excel (lokalt, COM)",    PhaseLocation.LOCAL),
        Phase("step6_fallback", "Step 6 -- Fall_Back_Logic",        PhaseLocation.LOCAL),
    ]
    return RunStatus(
        run_id=run_id,
        git_sha=git_sha,
        triggered_by=triggered_by,
        state=RunState.PENDING,
        started_at=utcnow_iso(),
        last_heartbeat=utcnow_iso(),
        phases=phases,
    )


# ---------------------------------------------------------------------
# Sjalvtest -- kor 'python run_status.py' for att verifiera round-trip
# utan nagon Azure-koppling. Ger ett snabbt kvitto pa att kontraktet
# serialiserar/deserialiserar konsekvent.
# ---------------------------------------------------------------------
if __name__ == "__main__":
    rs = default_pipeline(run_id="2026-06-12T0800Z", git_sha="abc1234", triggered_by="kollega@evidensia.se")
    rs.start_phase("step1_dataprep")
    rs.finish_phase("step1_dataprep", ok=True, note="13223 koder")
    rs.start_phase("step4_summary")
    rs.beat()
    rs.mark_waiting("Vantar pa lokal Excel-korning (steg 5) pa Windows -- LB.44")

    s = rs.to_json()
    print(s)
    rs2 = RunStatus.from_json(s)
    assert rs2.run_id == rs.run_id
    assert rs2.state == RunState.WAITING
    assert rs2.phases[1].note == "13223 koder"

    # --- Tidtagningstest: simulera varaktigheter genom att satta tider direkt ---
    rs.phases[0].started_at  = "2026-06-12T08:00:00Z"
    rs.phases[0].finished_at = "2026-06-12T08:04:30Z"   # 4m 30s
    rs.phases[3].started_at  = "2026-06-12T08:10:00Z"   # paus 5m30s emellan
    rs.phases[3].finished_at = "2026-06-12T11:22:00Z"   # 3h 12m
    assert rs.phases[0].duration_human == "4m 30s", rs.phases[0].duration_human
    assert rs.total_active_seconds == 270 + (3*3600 + 12*60), rs.total_active_seconds
    # Vaggklocka: 08:00:00 -> 11:22:00 = 3h 22m (inkl 5m30s paus)
    assert rs.wall_clock_human == "3h 22m 0s", rs.wall_clock_human

    print("\n" + rs.timing_summary())
    print("\nOK: round-trip + tidtagning konsekvent, kontraktsversion", CONTRACT_VERSION)
