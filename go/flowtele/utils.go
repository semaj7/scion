package main

// Process1 calls `fn` for each value received from any of the `chans`
// channels. The arguments to `fn` are the index of the channel the
// value came from and the string value. Process1 returns once all the
// channels are closed.
func Process1(chans []<-chan string, fn func(int, string)) {
    // Setup
    type item struct {
        int    // index of which channel this came from
        string // the actual string item
    }
    merged := make(chan item)
    var wg sync.WaitGroup
    wg.Add(len(chans))
    for i, c := range chans {
        go func(i int, c <-chan string) {
            // Reads and buffers a single item from `c` before
            // we even know if we can write to `merged`.
            //
            // Go doesn't provide a way to do something like:
            //     merged <- (<-c)
            // atomically, where we delay the read from `c`
            // until we can write to `merged`. The read from
            // `c` will always happen first (blocking as
            // required) and then we block on `merged` (with
            // either the above or the below syntax making
            // no difference).
            for s := range c {
                merged <- item{i, s}
            }
            // If/when this input channel is closed we just stop
            // writing to the merged channel and via the WaitGroup
            // let it be known there is one fewer channel active.
            wg.Done()
        }(i, c)
    }
    // One extra goroutine to watch for all the merging goroutines to
    // be finished and then close the merged channel.
    go func() {
        wg.Wait()
        close(merged)
    }()

    // "select-like" loop
    for i := range merged {
        // Process each value
        fn(i.int, i.string)
    }
}
