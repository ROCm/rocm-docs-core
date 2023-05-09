$(document).ready(function(){
    if (window.ResizeObserver) {
        document.body.addEventListener("bodyresize", event => {
            const { contentRect } = event.detail;
            const { width } = contentRect;
            if (window.prevWidth) {

            }
            if ((window.prevWidth && window.prevWidth > 960) && width < 960) {
                $("input#__primary").prop("checked", false);
            }
            window.prevWidth = width;
        })

        const onResizeCallback = (() => {
            let initial = true;
            let timeout;
            return entries => {
              if (initial) {
                initial = false;
                return;
              }
              clearTimeout(timeout)
              timeout = setTimeout(() => {
                for (const entry of entries) {
                  const event = new CustomEvent('bodyresize', {
                    detail: entry
                  });
                  entry.target.dispatchEvent(event);
                }
              }, 200);
            }
          })()

        window.resizeObserver = new ResizeObserver(onResizeCallback)
        window.resizeObserver.observe(document.body);
    } else {
        console.error("ResizeObserver not supported.")
    }
})
