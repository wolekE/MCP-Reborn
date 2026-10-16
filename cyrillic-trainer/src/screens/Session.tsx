import { useEffect, useState } from 'react'
import { Play } from '../modes/Play'
import { navigate } from '../router'
import { lettersToLearn } from '../session/items'
import { unlockedIds } from '../srs/scheduler'
import { useStore } from '../state/store'

/** "Start session": meet any newly unlocked letters first, otherwise run the daily review. */
export function Session() {
  const { save } = useStore()
  const [hasNew] = useState(() => lettersToLearn(save, unlockedIds(save.unlockedBatches)).length > 0)
  useEffect(() => {
    if (hasNew) navigate('learn', { replace: true })
  }, [hasNew])
  return hasNew ? null : <Play mode="review" />
}
