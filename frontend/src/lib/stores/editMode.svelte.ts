/** Global iOS-style "wiggle" mode: tiles jiggle and become draggable. */
class EditMode {
  active = $state(false);

  enter() {
    this.active = true;
  }

  exit() {
    this.active = false;
  }

  toggle() {
    this.active = !this.active;
  }
}

export const editMode = new EditMode();
