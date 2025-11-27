/** * 对应后端的 'Race' 模型
 */
export interface Race {
  race_id: number
  race_name: string
}

/** * 对应后端的 'Edition' 模型
 */
export interface Edition {
  edition_id: number
  race_id: number
  year: number
}

/** * 对应后端的 'Stage' 模型
 */
export interface Stage {
  stage_id: number
  edition_id: number
  stage_number: number // API 返回的是 float
  stage_route: string
}

/** * 对应后端的 'StageResult' 模型
 */
export interface StageResult {
  result_id: number
  stage_id: number
  rider_id: number
  team_id: number
  rank: number
  time_in_seconds: number
  rider_name?: string // API 内联
  team_name?: string // API 内联
}

/** * 对应后端的 'Rider' 模型
 */
export interface Rider {
  rider_id: number
  rider_name: string
}

/** * 对应后端的 'Team' 模型
 */
export interface Team {
  team_id: number
  team_name: string
}

/** * 车手详情统计数据
 */
export interface RiderDetail {
  rider: Rider
  total_races: number
  stage_wins: number
  teams: Team[]
}

// --- API 响应的特定类型 ---

/** * 响应 /api/races/:id/editions
 */
export interface ApiRaceEditions {
  race: string
  editions: Edition[]
}

/** * 响应 /api/editions/:id/stages
 */
export interface ApiEditionStages {
  edition_year: number
  race_name: string
  stages: Stage[]
}

/** * 响应 /api/stages/:id/results
 */
export interface ApiStageResults {
  stage_info: Stage
  results: StageResult[]
}

/** * 响应 /api/riders/:id
 */
export interface ApiRiderDetail {
  rider: Rider
  stats: {
    total_races: number
    stage_wins: number
    teams: Team[]
  }
}

/** * 车手参赛记录
 */
export interface RiderRaceRecord {
  result_id: number
  race_name: string
  year: number
  stage_number: number
  stage_route: string
  rank: number
  time_in_seconds: number
  team_name: string
}

/** * 响应 /api/riders/:id/races
 */
export interface ApiRiderRaces {
  rider: Rider
  race_records: RiderRaceRecord[]
}

/** * 车手冠军记录
 */
export interface RiderWinRecord {
  result_id: number
  race_name: string
  year: number
  stage_number: number
  stage_route: string
  time_in_seconds: number
  team_name: string
}

/** * 响应 /api/riders/:id/wins
 */
export interface ApiRiderWins {
  rider: Rider
  win_records: RiderWinRecord[]
}
